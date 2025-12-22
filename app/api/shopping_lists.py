"""
Shopping lists API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
from app.core.dependencies import get_current_user_id
from app.services.shopping_list_service import ShoppingListService
from app.services.predictor_service import PredictorService
from app.schemas.shopping_list import (
    ShoppingListCreate, ShoppingListResponse, ShoppingListUpdate,
    ShoppingListItemCreate, ShoppingListItemResponse, ShoppingListItemUpdate
)

router = APIRouter(prefix="/shopping-lists", tags=["shopping-lists"])


def get_shopping_list_service(supabase: Client = Depends(get_supabase)) -> ShoppingListService:
    """Dependency to get shopping list service"""
    return ShoppingListService(supabase)


def get_predictor_service(supabase: Client = Depends(get_supabase)) -> PredictorService:
    """Dependency to get predictor service"""
    return PredictorService(supabase)


# Shopping Lists
@router.get("", response_model=List[ShoppingListResponse])
def get_shopping_lists(
    status: Optional[str] = None,
    user_id: UUID = Depends(get_current_user_id),
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Get all shopping lists for a user"""
    lists = service.get_shopping_lists(user_id, status)
    return lists


@router.get("/{shopping_list_id}", response_model=ShoppingListResponse)
def get_shopping_list(
    shopping_list_id: UUID,
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Get a specific shopping list with items"""
    shopping_list = service.get_shopping_list(shopping_list_id)
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return shopping_list


@router.post("", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
def create_shopping_list(
    shopping_list: ShoppingListCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Create a new shopping list"""
    new_list = service.create_shopping_list(user_id, shopping_list)
    return new_list


@router.put("/{shopping_list_id}", response_model=ShoppingListResponse)
def update_shopping_list(
    shopping_list_id: UUID,
    shopping_list: ShoppingListUpdate,
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Update a shopping list"""
    updated_list = service.update_shopping_list(shopping_list_id, shopping_list)
    if not updated_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return updated_list


@router.delete("/{shopping_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shopping_list(
    shopping_list_id: UUID,
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Delete a shopping list"""
    deleted = service.delete_shopping_list(shopping_list_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Shopping list not found")


# Shopping List Items
@router.get("/{shopping_list_id}/items", response_model=List[ShoppingListItemResponse])
def get_shopping_list_items(
    shopping_list_id: UUID,
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Get all items in a shopping list"""
    items = service.get_shopping_list_items(shopping_list_id)
    return items


@router.get("/items/{item_id}", response_model=ShoppingListItemResponse)
def get_shopping_list_item(
    item_id: UUID,
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Get a specific shopping list item"""
    item = service.get_shopping_list_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Shopping list item not found")
    return item


@router.post("/{shopping_list_id}/items", response_model=ShoppingListItemResponse, status_code=status.HTTP_201_CREATED)
def create_shopping_list_item(
    shopping_list_id: UUID,
    item: ShoppingListItemCreate,
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Create a new shopping list item"""
    new_item = service.create_shopping_list_item(shopping_list_id, item)
    return new_item


@router.put("/items/{item_id}", response_model=ShoppingListItemResponse)
def update_shopping_list_item(
    item_id: UUID,
    item: ShoppingListItemUpdate,
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Update a shopping list item"""
    updated_item = service.update_shopping_list_item(item_id, item)
    if not updated_item:
        raise HTTPException(status_code=404, detail="Shopping list item not found")
    return updated_item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shopping_list_item(
    item_id: UUID,
    service: ShoppingListService = Depends(get_shopping_list_service)
):
    """Delete a shopping list item"""
    deleted = service.delete_shopping_list_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Shopping list item not found")


@router.post("/{shopping_list_id}/complete")
def complete_shopping_list(
    shopping_list_id: UUID,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    service: ShoppingListService = Depends(get_shopping_list_service),
    predictor_service: PredictorService = Depends(get_predictor_service)
):
    """
    Complete shopping list: update all items with product_id to FULL state in inventory
    and update the predictor model
    """
    try:
        result = service.complete_shopping_list(shopping_list_id, user_id)
        
        # Update predictor model for each product in background
        for log_id in result.get("log_ids", []):
            try:
                background_tasks.add_task(
                    predictor_service.process_inventory_log,
                    log_id=str(log_id)
                )
            except Exception as e:
                print(f"Error scheduling predictor update for log_id {log_id}: {e}")
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete shopping list: {str(e)}")

