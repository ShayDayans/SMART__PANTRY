"""
Inventory API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
from app.services.inventory_service import InventoryService
from app.services.predictor_service import PredictorService
from app.schemas.inventory import (
    InventoryCreate, InventoryResponse, InventoryUpdate,
    InventoryLogCreate, InventoryLogResponse
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def get_inventory_service(supabase: Client = Depends(get_supabase)) -> InventoryService:
    """Dependency to get inventory service"""
    return InventoryService(supabase)


def get_predictor_service(supabase: Client = Depends(get_supabase)) -> PredictorService:
    """Dependency to get predictor service"""
    return PredictorService(supabase)


@router.get("", response_model=List[InventoryResponse])
def get_inventory(
    user_id: UUID,
    service: InventoryService = Depends(get_inventory_service)
):
    """Get all inventory items for a user"""
    items = service.get_inventory(user_id)
    return items


@router.get("/{product_id}", response_model=InventoryResponse)
def get_inventory_item(
    user_id: UUID,
    product_id: UUID,
    service: InventoryService = Depends(get_inventory_service)
):
    """Get a specific inventory item"""
    item = service.get_inventory_item(user_id, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory(
    user_id: UUID,
    inventory: InventoryCreate,
    service: InventoryService = Depends(get_inventory_service)
):
    """Create or update an inventory item"""
    item = service.create_inventory(user_id, inventory)
    return item


@router.put("/{product_id}", response_model=InventoryResponse)
def update_inventory(
    user_id: UUID,
    product_id: UUID,
    inventory: InventoryUpdate,
    background_tasks: BackgroundTasks,
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
                user_id=user_id,
                product_id=product_id
            )
        except Exception as e:
            print(f"Error scheduling predictor update: {e}")
    
    return item


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(
    user_id: UUID,
    product_id: UUID,
    service: InventoryService = Depends(get_inventory_service)
):
    """Delete an inventory item"""
    deleted = service.delete_inventory(user_id, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Inventory item not found")


@router.post("/log", response_model=InventoryLogResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_log(
    user_id: UUID,
    log: InventoryLogCreate,
    service: InventoryService = Depends(get_inventory_service)
):
    """Create an inventory log entry"""
    log_entry = service.create_inventory_log(user_id, log)
    return log_entry


@router.get("/log", response_model=List[InventoryLogResponse])
def get_inventory_logs(
    user_id: UUID,
    product_id: Optional[UUID] = None,
    limit: int = 100,
    service: InventoryService = Depends(get_inventory_service)
):
    """Get inventory logs for a user"""
    logs = service.get_inventory_logs(user_id, product_id, limit)
    return logs

