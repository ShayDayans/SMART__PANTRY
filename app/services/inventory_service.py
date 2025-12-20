"""
Inventory service using Supabase API
"""
from typing import List, Optional
from uuid import UUID
from supabase import Client
from datetime import datetime
from app.schemas.inventory import InventoryCreate, InventoryUpdate, InventoryLogCreate
from app.models.enums import InventoryState, InventorySource, InventoryAction


class InventoryService:
    """Service for inventory operations using Supabase API"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def get_inventory(
        self, 
        user_id: UUID, 
        category_id: Optional[UUID] = None,
        state: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[dict]:
        """Get all inventory items for a user with optional filtering"""
        # Select with products join to get category info
        query = self.supabase.table("inventory").select("*, products(*, product_categories(*))").eq("user_id", str(user_id))
        
        # Filter by state
        if state:
            query = query.eq("state", state)
        
        response = query.execute()
        results = response.data if response.data else []
        
        # Filter by category (client-side filtering after join)
        if category_id:
            category_id_str = str(category_id)
            results = [
                item for item in results
                if isinstance(item.get("products"), dict) 
                and item.get("products", {}).get("category_id") == category_id_str
            ]
        
        # Apply search filter (client-side filtering)
        if search:
            search_lower = search.lower()
            results = [
                item for item in results
                if search_lower in item.get("displayed_name", "").lower() 
                or (item.get("products", {}).get("product_name", "").lower() if isinstance(item.get("products"), dict) else "")
            ]
        
        return results
    
    def get_inventory_item(self, user_id: UUID, product_id: UUID) -> Optional[dict]:
        """Get a specific inventory item"""
        response = self.supabase.table("inventory").select("*").eq("user_id", str(user_id)).eq("product_id", str(product_id)).execute()
        return response.data[0] if response.data else None
    
    def create_inventory(self, user_id: UUID, inventory: InventoryCreate) -> dict:
        """Create or update an inventory item"""
        data = {
            "user_id": str(user_id),
            "product_id": str(inventory.product_id),
            "state": inventory.state.value,
            "estimated_qty": inventory.estimated_qty,
            "qty_unit": inventory.qty_unit,
            "confidence": inventory.confidence,
            "last_source": inventory.last_source.value,
            "displayed_name": inventory.displayed_name,
        }
        # Upsert (insert or update)
        response = self.supabase.table("inventory").upsert(data, on_conflict="user_id,product_id").execute()
        return response.data[0] if response.data else {}
    
    def update_inventory(self, user_id: UUID, product_id: UUID, inventory: InventoryUpdate, log_change: bool = True) -> Optional[dict]:
        """Update an inventory item and optionally log the change"""
        # Get current state before updating (for logging)
        old_item = None
        if log_change and inventory.state is not None:
            old_item = self.get_inventory_item(user_id, product_id)
        
        data = {}
        if inventory.state is not None:
            data["state"] = inventory.state.value
        if inventory.estimated_qty is not None:
            data["estimated_qty"] = inventory.estimated_qty
        if inventory.qty_unit is not None:
            data["qty_unit"] = inventory.qty_unit
        if inventory.confidence is not None:
            data["confidence"] = inventory.confidence
        if inventory.last_source is not None:
            data["last_source"] = inventory.last_source.value
        if inventory.displayed_name is not None:
            data["displayed_name"] = inventory.displayed_name
        
        if not data:
            print(f"No data to update for user_id={user_id}, product_id={product_id}")
            return None
        
        # IMPORTANT: Actually update the inventory in the database
        try:
            print(f"Updating inventory: user_id={user_id}, product_id={product_id}, data={data}")
            response = self.supabase.table("inventory").update(data).eq("user_id", str(user_id)).eq("product_id", str(product_id)).execute()
            print(f"Update response: {response.data}")
            updated_item = response.data[0] if response.data else None
            
            if not updated_item:
                print(f"WARNING: Inventory update returned no data!")
                return None
        except Exception as e:
            print(f"ERROR updating inventory: {e}")
            raise
        
        # Log the state change if requested
        if log_change and inventory.state is not None and old_item:
            old_state = old_item.get("state")
            new_state = inventory.state.value
            
            if old_state != new_state:
                # Determine action based on state change
                action = InventoryAction.ADJUST
                
                # Create log entry
                log_data = {
                    "user_id": str(user_id),
                    "product_id": str(product_id),
                    "action": action.value,
                    "delta_state": new_state,
                    "action_confidence": inventory.confidence if inventory.confidence else 1.0,
                    "source": inventory.last_source.value if inventory.last_source else InventorySource.MANUAL.value,
                    "note": f"State changed from {old_state} to {new_state} via UI",
                }
                try:
                    self.supabase.table("inventory_log").insert(log_data).execute()
                    print(f"Log entry created: {old_state} -> {new_state}")
                except Exception as e:
                    # Log error but don't fail the update
                    print(f"Error logging inventory change: {e}")
        
        return updated_item
    
    def delete_inventory(self, user_id: UUID, product_id: UUID) -> bool:
        """Delete an inventory item"""
        response = self.supabase.table("inventory").delete().eq("user_id", str(user_id)).eq("product_id", str(product_id)).execute()
        return len(response.data) > 0
    
    def create_inventory_log(self, user_id: UUID, log: InventoryLogCreate) -> dict:
        """Create an inventory log entry"""
        data = {
            "user_id": str(user_id),
            "product_id": str(log.product_id),
            "action": log.action.value,
            "delta_state": log.delta_state.value if log.delta_state else None,
            "action_confidence": log.action_confidence,
            "source": log.source.value,
            "receipt_item_id": str(log.receipt_item_id) if log.receipt_item_id else None,
            "shopping_list_item_id": str(log.shopping_list_item_id) if log.shopping_list_item_id else None,
            "note": log.note,
        }
        response = self.supabase.table("inventory_log").insert(data).execute()
        return response.data[0] if response.data else {}
    
    def get_inventory_logs(self, user_id: UUID, product_id: Optional[UUID] = None, limit: int = 100) -> List[dict]:
        """Get inventory logs for a user, optionally filtered by product"""
        query = self.supabase.table("inventory_log").select("*").eq("user_id", str(user_id))
        if product_id:
            query = query.eq("product_id", str(product_id))
        response = query.order("occurred_at", desc=True).limit(limit).execute()
        return response.data if response.data else []

