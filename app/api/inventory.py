"""
Inventory API routes
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from typing import List, Optional
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
from app.core.dependencies import get_current_user_id

logger = logging.getLogger(__name__)
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
    
    # NOTE: We do NOT trigger predictor update here anymore.
    # The model should only learn from real events (EMPTY, PURCHASE, MORE/LESS, WASTED),
    # not from manual inventory state changes.
    # Manual state changes are just UI updates, not consumption events.
    
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
    
    # Update days_left immediately (but NOT cycle_mean_days)
    # cycle_mean_days will be updated only during weekly update based on observed cycle length
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    try:
        # Get current state to calculate new days_left
        predictor_profile_id, cfg = predictor_service._load_cfg_and_profile(str(user_id))
        products = dict(predictor_service.repo.get_user_inventory_products(str(user_id)))
        category_id = products.get(str(product_id))
        state = predictor_service._load_or_init_state(
            str(user_id), str(product_id), predictor_profile_id, cfg, category_id, now
        )
        
        # Get current days_left from inventory (if user has updated it)
        current_item = service.get_inventory_item(user_id, product_id)
        inventory_days_left = current_item.get("estimated_qty") if current_item else None
        if inventory_days_left is not None:
            try:
                inventory_days_left = float(inventory_days_left)
            except (ValueError, TypeError):
                inventory_days_left = None
        
        from ema_cycle_predictor import compute_days_left, predict, derive_state
        mult = predictor_service.repo.get_active_habit_multiplier(str(user_id), str(product_id), category_id, now)
        # Use inventory_days_left if available, otherwise calculate from cycle_mean_days
        current_days_left = compute_days_left(state, now, mult, cfg, inventory_days_left=inventory_days_left)
        
        # Check if product is EMPTY (days_left = 0 or very close to 0)
        is_empty = current_days_left <= 0.01 or (current_item and current_item.get("state") == "EMPTY")
        
        # Apply percentage multiplier to days_left based on direction
        if is_empty:
            # Special handling for EMPTY products
            if direction.lower() == "more":
                # If EMPTY and MORE: increase moderately by 0.15 * cycle_mean_days
                # This means the user is indicating they have the product again
                if state.cycle_mean_days > 0:
                    # Moderate increase: 15% of the mean (not 115%!)
                    new_days_left = state.cycle_mean_days * 0.15
                else:
                    # If no cycle_mean_days yet, start with a small value (1-2 days)
                    new_days_left = 1.5
                # Reset empty_at since user indicates they have the product
                state.empty_at = None
                logger.info(f"[EMPTY->MORE] Moderate increase for product {product_id}: days_left = {new_days_left} (from cycle_mean_days = {state.cycle_mean_days}), empty_at reset")
            else:  # less
                # If EMPTY and LESS: stay at 0 (or very small value)
                new_days_left = 0.0
                # empty_at stays as is (not reset)
                logger.info(f"[EMPTY->LESS] Product {product_id} stays EMPTY")
        else:
            # Normal case: product has days_left > 0
            if direction.lower() == "more":
                multiplier = 1.15  # 15% more days
            else:  # less
                multiplier = 0.85  # 15% less days
            
            new_days_left = current_days_left * multiplier
            new_days_left = max(0.0, new_days_left)  # Can't be negative
        
        # Calculate new state based on new days_left
        new_state = derive_state(new_days_left, state.cycle_mean_days, cfg)
        
        # Update state.last_pred_days_left to reflect the new prediction
        state.last_pred_days_left = float(new_days_left)
        state.last_update_at = now
        
        # Calculate confidence
        from ema_cycle_predictor import compute_confidence
        confidence = compute_confidence(state, now, cfg)
        
        # Update product_predictor_state with updated state
        params_json = state.to_params_json()
        params_json = predictor_service._make_json_serializable(params_json)
        predictor_service.repo.upsert_predictor_state(
            user_id=str(user_id),
            product_id=str(product_id),
            predictor_profile_id=predictor_profile_id,
            params=params_json,
            confidence=confidence,
            updated_at=now,
        )
        
        # Update inventory with new days_left (but keep cycle_mean_days unchanged)
        print(f"[DEBUG provide_feedback] Updating inventory: user_id={user_id}, product_id={product_id}, new_days_left={new_days_left}, new_state={new_state.value}, confidence={confidence}")
        try:
            predictor_service.repo.upsert_inventory_days_estimate(
                user_id=str(user_id),
                product_id=str(product_id),
                days_left=new_days_left,
                state=InventoryState(new_state.value),
                confidence=confidence,
                source=InventorySource.MANUAL,
            )
            print(f"[DEBUG provide_feedback] Successfully updated inventory")
        except Exception as e:
            print(f"[ERROR provide_feedback] Failed to update inventory: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"Warning: Could not update days_left: {e}")
    
    return {
        "message": f"Days left updated: {direction} feedback applied (cycle_mean_days unchanged until weekly update)",
        "log_id": log_entry.get("log_id") if log_entry else None,
        "note": "cycle_mean_days will be updated during weekly update based on observed cycle length"
    }


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
    
    # IMPORTANT: Save current state BEFORE any updates (needed for predictor)
    # This is the state before we update inventory to EMPTY or FULL
    current_state_before_update = InventoryState(current_item.get("state", "UNKNOWN"))
    
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
            
            # Process purchase log for predictor with state BEFORE purchase
            # Use the state we saved at the beginning (before any updates)
            if purchase_log_entry:
                background_tasks.add_task(
                    predictor_service.process_inventory_log,
                    log_id=str(purchase_log_entry.get("log_id")),
                    state_before_purchase=current_state_before_update
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

