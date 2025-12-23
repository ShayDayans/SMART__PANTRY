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
        # If filtering by category, first get all product_ids in that category
        product_ids_filter = None
        if category_id:
            products_response = self.supabase.table("products").select("product_id").eq("category_id", str(category_id)).execute()
            if products_response.data:
                product_ids = [item["product_id"] for item in products_response.data]
                if product_ids:
                    product_ids_filter = product_ids
                else:
                    # No products in this category, return empty list
                    return []
        
        # Build query - get inventory with products
        # First get basic inventory with products (without nested categories)
        query = self.supabase.table("inventory").select(
            "*, "
            "products("
            "product_id, "
            "product_name, "
            "category_id, "
            "default_unit, "
            "barcode"
            ")"
        ).eq("user_id", str(user_id))
        
        # Filter by category (server-side using product_ids)
        if product_ids_filter:
            # Supabase PostgREST supports filtering by array using .in_()
            # Convert UUIDs to strings for filtering
            product_ids_str = [str(pid) for pid in product_ids_filter]
            query = query.in_("product_id", product_ids_str)
        
        # Filter by state
        if state:
            query = query.eq("state", state)
        
        try:
            response = query.execute()
            results = response.data if response.data else []
            
            # Debug: log first item structure to see what we're getting
            if results and len(results) > 0:
                import json
                print(f"[DEBUG Inventory] Total items: {len(results)}")
                print(f"[DEBUG Inventory] First item structure: {json.dumps(results[0], indent=2, default=str)}")
                
                # Check if products and categories are present
                first_item = results[0]
                if "products" in first_item:
                    products_data = first_item["products"]
                    print(f"[DEBUG Inventory] Products data type: {type(products_data)}")
                    print(f"[DEBUG Inventory] Products data: {json.dumps(products_data, indent=2, default=str)}")
                else:
                    print(f"[DEBUG Inventory] WARNING: No 'products' key in inventory item!")
        except Exception as e:
            print(f"[ERROR Inventory] Failed to execute query: {e}")
            import traceback
            traceback.print_exc()
            results = []
        
        # Post-process: Fetch and attach category information
        # Get all unique category_ids from products
        category_ids = set()
        for item in results:
            if "products" in item and isinstance(item["products"], dict):
                products = item["products"]
                category_id = products.get("category_id")
                if category_id:
                    category_ids.add(str(category_id))
        
        # Fetch all categories in one query
        categories_map = {}
        if category_ids:
            try:
                categories_response = self.supabase.table("product_categories").select(
                    "category_id, category_name"
                ).in_("category_id", list(category_ids)).execute()
                
                if categories_response.data:
                    for cat in categories_response.data:
                        categories_map[str(cat["category_id"])] = cat
            except Exception as e:
                print(f"[WARNING Inventory] Failed to fetch categories: {e}")
        
        # Attach category information to each product
        for item in results:
            if "products" in item and isinstance(item["products"], dict):
                products = item["products"]
                category_id = products.get("category_id")
                
                # Debug: log category_id for each item
                if category_id:
                    print(f"[DEBUG Inventory] Item {item.get('product_id')}: category_id={category_id}")
                    category_id_str = str(category_id)
                    if category_id_str in categories_map:
                        # Attach category info directly to products
                        products["product_categories"] = categories_map[category_id_str]
                        print(f"[DEBUG Inventory] Attached category {categories_map[category_id_str].get('category_name')} to product {item.get('product_id')}")
                    else:
                        print(f"[WARNING Inventory] Category {category_id_str} not found in categories_map")
                else:
                    print(f"[DEBUG Inventory] Item {item.get('product_id')}: No category_id")
            else:
                # Debug: log if products is missing or wrong type
                print(f"[WARNING Inventory] Item {item.get('product_id')}: products missing or wrong type. Has 'products' key: {'products' in item}, Type: {type(item.get('products'))}")
        
        # Apply search filter (client-side filtering as it's text search)
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

