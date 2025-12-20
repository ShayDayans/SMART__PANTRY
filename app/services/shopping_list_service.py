"""
Shopping list service using Supabase API
"""
from typing import List, Optional
from uuid import UUID
from supabase import Client
from app.schemas.shopping_list import ShoppingListCreate, ShoppingListUpdate, ShoppingListItemCreate, ShoppingListItemUpdate


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

