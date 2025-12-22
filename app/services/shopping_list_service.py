"""
Shopping list service using Supabase API
"""
from typing import List, Optional
from uuid import UUID
from supabase import Client
from app.schemas.shopping_list import ShoppingListCreate, ShoppingListUpdate, ShoppingListItemCreate, ShoppingListItemUpdate
from app.models.enums import ShoppingListStatus


class ShoppingListService:
    """Service for shopping list operations using Supabase API"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    # Shopping Lists
    def get_shopping_lists(self, user_id: UUID, status: Optional[str] = None) -> List[dict]:
        """Get all shopping lists for a user"""
        query = self.supabase.table("shopping_list").select("*, shopping_list_items(*)").eq("user_id", str(user_id))
        if status:
            query = query.eq("status", status)
        response = query.order("created_at", desc=True).execute()
        return response.data if response.data else []
    
    def get_shopping_list(self, shopping_list_id: UUID) -> Optional[dict]:
        """Get a specific shopping list with items"""
        response = self.supabase.table("shopping_list").select("*, shopping_list_items(*)").eq("shopping_list_id", str(shopping_list_id)).execute()
        return response.data[0] if response.data else None
    
    def create_shopping_list(self, user_id: UUID, shopping_list: ShoppingListCreate) -> dict:
        """Create a new shopping list"""
        data = {
            "user_id": str(user_id),
            "title": shopping_list.title,
            "status": shopping_list.status.value,
            "notes": shopping_list.notes,
        }
        response = self.supabase.table("shopping_list").insert(data).execute()
        return response.data[0] if response.data else {}
    
    def update_shopping_list(self, shopping_list_id: UUID, shopping_list: ShoppingListUpdate) -> Optional[dict]:
        """Update a shopping list"""
        data = {}
        if shopping_list.title is not None:
            data["title"] = shopping_list.title
        if shopping_list.status is not None:
            data["status"] = shopping_list.status.value
        if shopping_list.notes is not None:
            data["notes"] = shopping_list.notes
        
        if not data:
            return None
        
        response = self.supabase.table("shopping_list").update(data).eq("shopping_list_id", str(shopping_list_id)).execute()
        return response.data[0] if response.data else None
    
    def delete_shopping_list(self, shopping_list_id: UUID) -> bool:
        """Delete a shopping list (cascade deletes items)"""
        response = self.supabase.table("shopping_list").delete().eq("shopping_list_id", str(shopping_list_id)).execute()
        return len(response.data) > 0
    
    # Shopping List Items
    def get_shopping_list_items(self, shopping_list_id: UUID) -> List[dict]:
        """Get all items in a shopping list"""
        response = self.supabase.table("shopping_list_items").select("*, products(*)").eq("shopping_list_id", str(shopping_list_id)).execute()
        return response.data if response.data else []
    
    def get_shopping_list_item(self, item_id: UUID) -> Optional[dict]:
        """Get a specific shopping list item"""
        response = self.supabase.table("shopping_list_items").select("*, products(*)").eq("shopping_list_item_id", str(item_id)).execute()
        return response.data[0] if response.data else None
    
    def create_shopping_list_item(self, shopping_list_id: UUID, item: ShoppingListItemCreate) -> dict:
        """Create a new shopping list item"""
        # Validate: either product_id or free_text_name must be set
        if not item.product_id and not item.free_text_name:
            raise ValueError("Either product_id or free_text_name must be provided")
        if item.product_id and item.free_text_name:
            raise ValueError("Cannot set both product_id and free_text_name")
        
        data = {
            "shopping_list_id": str(shopping_list_id),
            "product_id": str(item.product_id) if item.product_id else None,
            "free_text_name": item.free_text_name,
            "recommended_qty": item.recommended_qty,
            "unit": item.unit,
            "user_qty_override": item.user_qty_override,
            "status": item.status.value,
            "priority": item.priority,
            "added_by": item.added_by.value,
        }
        response = self.supabase.table("shopping_list_items").insert(data).execute()
        return response.data[0] if response.data else {}
    
    def update_shopping_list_item(self, item_id: UUID, item: ShoppingListItemUpdate) -> Optional[dict]:
        """Update a shopping list item"""
        data = {}
        if item.product_id is not None:
            data["product_id"] = str(item.product_id)
        if item.free_text_name is not None:
            data["free_text_name"] = item.free_text_name
        if item.recommended_qty is not None:
            data["recommended_qty"] = item.recommended_qty
        if item.unit is not None:
            data["unit"] = item.unit
        if item.user_qty_override is not None:
            data["user_qty_override"] = item.user_qty_override
        if item.status is not None:
            data["status"] = item.status.value
        if item.priority is not None:
            data["priority"] = item.priority
        
        if not data:
            return None
        
        response = self.supabase.table("shopping_list_items").update(data).eq("shopping_list_item_id", str(item_id)).execute()
        return response.data[0] if response.data else None
    
    def delete_shopping_list_item(self, item_id: UUID) -> bool:
        """Delete a shopping list item"""
        response = self.supabase.table("shopping_list_items").delete().eq("shopping_list_item_id", str(item_id)).execute()
        return len(response.data) > 0
    
    def complete_shopping_list(self, shopping_list_id: UUID, user_id: UUID) -> dict:
        """
        Complete shopping list: update all items with product_id to FULL state in inventory
        and update the predictor model
        """
        from datetime import datetime, timezone
        from app.models.enums import InventoryState, InventorySource, InventoryAction
        
        # Get shopping list with items
        shopping_list = self.get_shopping_list(shopping_list_id)
        if not shopping_list:
            raise ValueError("Shopping list not found")
        
        # Update shopping list status to COMPLETED
        from app.models.enums import ShoppingListStatus
        self.update_shopping_list(shopping_list_id, ShoppingListUpdate(status=ShoppingListStatus.COMPLETED))
        
        items = shopping_list.get("shopping_list_items", [])
        inventory_updates = []
        log_ids = []
        
        # Get product service for product details
        from app.services.product_service import ProductService
        product_service = ProductService(self.supabase)
        
        for item in items:
            # Only process items that are marked as BOUGHT
            item_status = item.get("status", "").upper()
            if item_status != "BOUGHT":
                # Skip items that are not marked as bought
                continue
            
            product_id = item.get("product_id")
            if not product_id:
                # Skip items without product_id (free_text items)
                continue
            
            shopping_list_item_id = item.get("shopping_list_item_id")
            
            # Get product details
            product = product_service.get_product(UUID(product_id))
            if not product:
                continue
            
            # Check if product exists in user's inventory
            existing_inventory = self.supabase.table("inventory").select("*").eq(
                "user_id", str(user_id)
            ).eq("product_id", product_id).execute()
            
            # Update or create inventory item as FULL
            inventory_data = {
                "user_id": str(user_id),
                "product_id": product_id,
                "state": InventoryState.FULL.value,
                "last_source": InventorySource.SHOPPING_LIST.value,
                "displayed_name": product.get("product_name"),
                "qty_unit": product.get("default_unit", "units"),
                "confidence": 1.0
            }
            
            if existing_inventory.data and len(existing_inventory.data) > 0:
                # Update existing inventory
                update_result = self.supabase.table("inventory").update(inventory_data).eq(
                    "user_id", str(user_id)
                ).eq("product_id", product_id).execute()
            else:
                # Create new inventory item
                update_result = self.supabase.table("inventory").insert(inventory_data).execute()
            
            inventory_updates.append({
                "product_id": product_id,
                "product_name": product.get("product_name"),
                "state": InventoryState.FULL.value
            })
            
            # Create inventory log entry
            log_entry = {
                "user_id": str(user_id),
                "product_id": product_id,
                "action": InventoryAction.PURCHASE.value,
                "delta_state": InventoryState.FULL.value,
                "action_confidence": 1.0,
                "source": InventorySource.SHOPPING_LIST.value,
                "shopping_list_item_id": str(shopping_list_item_id),
                "note": f"Purchased from shopping list"
            }
            
            log_result = self.supabase.table("inventory_log").insert(log_entry).execute()
            if log_result.data and len(log_result.data) > 0:
                log_ids.append(log_result.data[0].get("log_id"))
        
        return {
            "shopping_list_id": str(shopping_list_id),
            "status": "COMPLETED",
            "inventory_updates": inventory_updates,
            "log_ids": log_ids
        }

