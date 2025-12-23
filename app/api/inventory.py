"""
Inventory API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from typing import List, Optional
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
from app.core.dependencies import get_current_user_id
from app.services.inventory_service import InventoryService
from app.services.predictor_service import PredictorService
from app.schemas.inventory import (
    InventoryCreate, InventoryResponse, InventoryUpdate,
    InventoryLogCreate, InventoryLogResponse, ProductActionRequest
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def get_inventory_service(supabase: Client = Depends(get_supabase)) -> InventoryService:
    """Dependency to get inventory service"""
    return InventoryService(supabase)


def get_predictor_service(supabase: Client = Depends(get_supabase)) -> PredictorService:
    """Dependency to get predictor service"""
    return PredictorService(supabase)


@router.get("")
def get_inventory(
    user_id: UUID = Depends(get_current_user_id),
    category_id: Optional[UUID] = None,
    state: Optional[str] = None,
    search: Optional[str] = None,
    service: InventoryService = Depends(get_inventory_service)
):
    """
    Get all inventory items for a user with optional filtering.
    Returns raw dicts to preserve nested products structure.
    
    - category_id: Filter by product category
    - state: Filter by inventory state (FULL, MEDIUM, LOW, EMPTY, UNKNOWN)
    - search: Search by product name (case-insensitive)
    """
    items = service.get_inventory(user_id, category_id=category_id, state=state, search=search)
    # Return raw dicts to preserve nested products structure
    # The InventoryResponse schema doesn't handle nested products well
    return items


@router.get("/{product_id}", response_model=InventoryResponse)
def get_inventory_item(
    product_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: InventoryService = Depends(get_inventory_service)
):
    """Get a specific inventory item"""
    item = service.get_inventory_item(user_id, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory(
    inventory: InventoryCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: InventoryService = Depends(get_inventory_service)
):
    """Create or update an inventory item"""
    item = service.create_inventory(user_id, inventory)
    return item


@router.put("/{product_id}", response_model=InventoryResponse)
def update_inventory(
    product_id: UUID,
    inventory: InventoryUpdate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    service: InventoryService = Depends(get_inventory_service),
    predictor_service: PredictorService = Depends(get_predictor_service)
):
    """Update an inventory item, log the change, and trigger predictor update"""
    # Ensure last_source is set to MANUAL for UI updates
    if inventory.last_source is None:
        from app.models.enums import InventorySource
        inventory.last_source = InventorySource.MANUAL
    
    # Update inventory (this will also log the change)
    item = service.update_inventory(user_id, product_id, inventory, log_change=True)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # ALWAYS trigger predictor to learn from the change (but don't overwrite manual changes)
    if inventory.state is not None:
      try:
        background_tasks.add_task(
          predictor_service.learn_from_manual_change,
          user_id=str(user_id),
          product_id=str(product_id)
        )
      except Exception as e:
        print(f"Error scheduling predictor update: {e}")
    
    return item


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(
    product_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: InventoryService = Depends(get_inventory_service)
):
    """Delete an inventory item"""
    deleted = service.delete_inventory(user_id, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Inventory item not found")


@router.post("/log", response_model=InventoryLogResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_log(
    log: InventoryLogCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    service: InventoryService = Depends(get_inventory_service),
    predictor_service: PredictorService = Depends(get_predictor_service)
):
    """Create an inventory log entry and trigger predictor update"""
    log_entry = service.create_inventory_log(user_id, log)
    
    # Trigger predictor to process this log entry and update inventory state
    if log_entry:
        try:
            background_tasks.add_task(
                predictor_service.process_inventory_log,
                log_id=str(log_entry.get("log_id"))
            )
        except Exception as e:
            print(f"Error scheduling predictor update: {e}")
    
    return log_entry


@router.post("/{product_id}/feedback")
def provide_feedback(
    product_id: UUID,
    direction: str = Query(..., description="Feedback direction: 'more' or 'less'"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_id: UUID = Depends(get_current_user_id),
    service: InventoryService = Depends(get_inventory_service),
    predictor_service: PredictorService = Depends(get_predictor_service)
):
    """
    Provide feedback to the model (More/Less) - only updates the model, not inventory state directly.
    The model will then update the inventory state based on its prediction.
    """
    from app.models.enums import InventoryAction, InventorySource, InventoryState
    
    # Get current inventory state to determine delta
    current_item = service.get_inventory_item(user_id, product_id)
    if not current_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    current_state = InventoryState(current_item.get("state", "UNKNOWN"))
    states = [InventoryState.FULL, InventoryState.MEDIUM, InventoryState.LOW, InventoryState.EMPTY]
    current_index = states.index(current_state) if current_state in states else 1  # Default to MEDIUM if unknown
    
    # Determine new state based on direction
    if direction.lower() == "more":
        new_index = max(0, current_index - 1)
        action = InventoryAction.ADJUST
        note = "User feedback: More stock needed"
    elif direction.lower() == "less":
        new_index = min(len(states) - 1, current_index + 1)
        action = InventoryAction.ADJUST
        note = "User feedback: Less stock needed"
    else:
        raise HTTPException(status_code=400, detail="Direction must be 'more' or 'less'")
    
    new_state = states[new_index]
    
    # Create log entry with feedback
    log_create = InventoryLogCreate(
        product_id=product_id,
        action=action,
        delta_state=new_state,
        action_confidence=1.0,
        source=InventorySource.MANUAL,
        note=note
    )
    
    try:
        log_entry = service.create_inventory_log(user_id, log_create)
    except Exception as e:
        # Log the error but don't fail the request - it's a network issue
        print(f"Error creating inventory log: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again in a moment."
        )
    
    # Trigger predictor to process this log entry
    if log_entry:
        try:
            background_tasks.add_task(
                predictor_service.process_inventory_log,
                log_id=str(log_entry.get("log_id"))
            )
        except Exception as e:
            print(f"Error scheduling predictor update: {e}")
    
    return {"message": "Model updated", "log_id": log_entry.get("log_id") if log_entry else None}


@router.get("/log", response_model=List[InventoryLogResponse])
def get_inventory_logs(
    product_id: Optional[UUID] = None,
    limit: int = 100,
    user_id: UUID = Depends(get_current_user_id),
    service: InventoryService = Depends(get_inventory_service)
):
    """Get inventory logs for a user"""
    logs = service.get_inventory_logs(user_id, product_id, limit)
    return logs


@router.post("/{product_id}/action", response_model=InventoryLogResponse, status_code=status.HTTP_201_CREATED)
def product_action(
    product_id: UUID,
    action_request: ProductActionRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_id: UUID = Depends(get_current_user_id),
    service: InventoryService = Depends(get_inventory_service),
    predictor_service: PredictorService = Depends(get_predictor_service)
):
    """
    Handle product action: thrown away, repurchased, or ran out.
    Creates inventory log entry and updates the predictor model.
    """
    from app.models.enums import InventoryAction, InventorySource, InventoryState
    
    # Map action_type to InventoryAction and note format
    action_type = action_request.action_type.lower()
    reason = action_request.reason
    custom_reason = action_request.custom_reason
    
    # Build the full reason text
    if custom_reason and custom_reason.strip():
        full_reason = f"{reason}: {custom_reason.strip()}"
    else:
        full_reason = reason
    
    # Determine action and note format based on action_type
    if action_type == "thrown_away":
        action = InventoryAction.TRASH
        # Format note for predictor to recognize as WASTED
        note = f"WASTED: {full_reason}"
        delta_state = InventoryState.EMPTY
        
    elif action_type == "repurchased":
        action = InventoryAction.REPURCHASE
        # Format note for predictor to recognize as PURCHASE
        note = f"PURCHASE: {full_reason}"
        delta_state = InventoryState.EMPTY  # Will be set to FULL after purchase
        
    elif action_type == "ran_out":
        action = InventoryAction.EMPTY
        # Format note for predictor to recognize as EMPTY
        note = f"EMPTY: {full_reason}"
        delta_state = InventoryState.EMPTY
        
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action_type: {action_request.action_type}")
    
    # Verify product exists
    current_item = service.get_inventory_item(user_id, product_id)
    if not current_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Create log entry
    log_create = InventoryLogCreate(
        product_id=product_id,
        action=action,
        delta_state=delta_state,
        action_confidence=1.0,
        source=InventorySource.MANUAL,
        note=note
    )
    
    try:
        log_entry = service.create_inventory_log(user_id, log_create)
    except Exception as e:
        print(f"Error creating inventory log: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create inventory log: {str(e)}"
        )
    
    # Update inventory state to EMPTY for all actions
    # (For repurchased, we'll update to FULL after processing)
    inventory_update = InventoryUpdate(
        state=InventoryState.EMPTY,
        confidence=1.0,
        last_source=InventorySource.MANUAL
    )
    try:
        service.update_inventory(user_id, product_id, inventory_update, log_change=False)
    except Exception as e:
        print(f"Warning: Could not update inventory state: {e}")
    
    # For repurchased, update to FULL after a moment (simulating purchase)
    if action_type == "repurchased":
        # Create a second log entry for the purchase
        purchase_log = InventoryLogCreate(
            product_id=product_id,
            action=InventoryAction.PURCHASE,
            delta_state=InventoryState.FULL,
            action_confidence=1.0,
            source=InventorySource.MANUAL,
            note=f"PURCHASE: {full_reason}"
        )
        try:
            purchase_log_entry = service.create_inventory_log(user_id, purchase_log)
            # Update inventory to FULL
            inventory_update_full = InventoryUpdate(
                state=InventoryState.FULL,
                confidence=1.0,
                last_source=InventorySource.MANUAL
            )
            service.update_inventory(user_id, product_id, inventory_update_full, log_change=False)
            
            # Process purchase log for predictor
            if purchase_log_entry:
                background_tasks.add_task(
                    predictor_service.process_inventory_log,
                    log_id=str(purchase_log_entry.get("log_id"))
                )
        except Exception as e:
            print(f"Warning: Could not create purchase log: {e}")
    
    # Trigger predictor to process this log entry
    if log_entry:
        try:
            background_tasks.add_task(
                predictor_service.process_inventory_log,
                log_id=str(log_entry.get("log_id"))
            )
        except Exception as e:
            print(f"Error scheduling predictor update: {e}")
    
    return log_entry

