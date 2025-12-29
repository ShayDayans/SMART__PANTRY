"""
Shopping list service using Supabase API
"""
from typing import List, Optional
from uuid import UUID
from supabase import Client
import math
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
    def get_shopping_list_items(self, shopping_list_id: UUID, user_id: Optional[UUID] = None) -> List[dict]:
        """Get all items in a shopping list, sorted by priority (DESC) then created_at (ASC), with prediction data"""
        response = self.supabase.table("shopping_list_items").select("*, products(*)").eq("shopping_list_id", str(shopping_list_id)).order("priority", desc=True).order("created_at", desc=False).execute()
        items = response.data if response.data else []
        
        # Add prediction data for items with product_id
        if user_id:
            shopping_freq_days = self._get_shopping_frequency_days(user_id)
            for item in items:
                product_id = item.get("product_id")
                if product_id:
                    prediction = self._get_item_prediction(user_id, UUID(product_id), shopping_freq_days)
                    if prediction:
                        item["prediction"] = prediction
        
        return items
    
    def _get_item_prediction(self, user_id: UUID, product_id: UUID, shopping_frequency_days: Optional[int] = None) -> Optional[dict]:
        """Get prediction data for a shopping list item"""
        try:
            # Get shopping frequency if not provided
            if shopping_frequency_days is None:
                shopping_frequency_days = self._get_shopping_frequency_days(user_id)
            
            # Get inventory item
            inventory_result = self.supabase.table("inventory").select("*").eq("user_id", str(user_id)).eq("product_id", str(product_id)).execute()
            
            if not inventory_result.data or len(inventory_result.data) == 0:
                # No inventory - return default prediction
                return {
                    "predicted_days_left": 0,
                    "predicted_state": "EMPTY",
                    "confidence": 0.0,
                    "will_sufficient": False
                }
            
            inventory_item = inventory_result.data[0]
            predicted_days_left = inventory_item.get("estimated_qty", 0)
            predicted_state = inventory_item.get("state", "UNKNOWN")
            confidence = inventory_item.get("confidence", 0.0)
            
            # Get recommended quantity to calculate if it will be sufficient
            recommended_qty = self._calculate_recommended_qty(user_id, product_id, shopping_frequency_days)
            
            # Get cycle_mean_days from predictor state
            predictor_result = self.supabase.table("product_predictor_state").select("params").eq("user_id", str(user_id)).eq("product_id", str(product_id)).execute()
            cycle_mean_days = 7.0  # Default
            if predictor_result.data and len(predictor_result.data) > 0:
                params = predictor_result.data[0].get("params", {})
                if isinstance(params, dict):
                    cycle_mean_days = params.get("cycle_mean_days", 7.0)
            
            # Calculate if recommended quantity will be sufficient
            # Will last: recommended_qty * cycle_mean_days days
            will_last_days = (recommended_qty or 1) * cycle_mean_days
            will_sufficient = will_last_days >= shopping_frequency_days
            
            return {
                "predicted_days_left": predicted_days_left,
                "predicted_state": predicted_state,
                "confidence": confidence,
                "recommended_qty": recommended_qty,
                "will_sufficient": will_sufficient,
                "will_last_days": will_last_days
            }
        except Exception as e:
            print(f"[ERROR] Failed to get item prediction: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_shopping_list_item(self, item_id: UUID) -> Optional[dict]:
        """Get a specific shopping list item"""
        response = self.supabase.table("shopping_list_items").select("*, products(*)").eq("shopping_list_item_id", str(item_id)).execute()
        return response.data[0] if response.data else None
    
    def _get_shopping_frequency_days(self, user_id: UUID) -> int:
        """Get user's shopping frequency in days from habits/preferences"""
        try:
            from app.services.habit_service import HabitService
            habit_service = HabitService(self.supabase)
            preferences = habit_service.get_user_preferences(str(user_id))
            
            shopping_freq = preferences.get("shopping_frequency")
            if shopping_freq == "WEEKLY":
                return 7
            elif shopping_freq == "BI_WEEKLY":
                return 14
            elif shopping_freq == "MONTHLY":
                return 30
            else:
                return 7  # Default to weekly
        except Exception as e:
            print(f"[WARNING] Could not get shopping frequency: {e}")
            return 7  # Default to weekly
    
    def _calculate_recommended_qty(self, user_id: UUID, product_id: UUID, shopping_frequency_days: int = 7) -> Optional[float]:
        """
        Calculate recommended quantity based on:
        - Current inventory state
        - Model prediction (cycle_mean_days)
        - Days until next shopping
        """
        try:
            # Get current inventory state
            inventory_result = self.supabase.table("inventory").select("*").eq("user_id", str(user_id)).eq("product_id", str(product_id)).execute()
            
            if not inventory_result.data or len(inventory_result.data) == 0:
                # No inventory - recommend based on shopping frequency and default cycle
                # Use default cycle_mean_days of 7 days
                recommended = max(1.0, math.ceil(shopping_frequency_days / 7.0))
                return recommended
            
            inventory_item = inventory_result.data[0]
            current_state = inventory_item.get("state", "UNKNOWN")
            estimated_qty = inventory_item.get("estimated_qty", 0)  # days left
            
            # Get predictor state to get cycle_mean_days
            predictor_result = self.supabase.table("product_predictor_state").select("params").eq("user_id", str(user_id)).eq("product_id", str(product_id)).execute()
            
            cycle_mean_days = 7.0  # Default
            if predictor_result.data and len(predictor_result.data) > 0:
                params = predictor_result.data[0].get("params", {})
                if isinstance(params, dict):
                    cycle_mean_days = params.get("cycle_mean_days", 7.0)
            
            # Calculate recommended quantity
            # Formula: (days_until_shopping - current_days_left) / cycle_mean_days
            days_until_shopping = shopping_frequency_days
            days_left = estimated_qty if estimated_qty > 0 else 0
            
            # If current state is LOW or EMPTY, we need more
            if current_state in ["LOW", "EMPTY"]:
                # Need enough for full shopping cycle
                recommended = max(1.0, math.ceil(days_until_shopping / cycle_mean_days))
            else:
                # Calculate how much more we need
                days_needed = max(0, days_until_shopping - days_left)
                recommended = max(1.0, math.ceil(days_needed / cycle_mean_days))
            
            return recommended
            
        except Exception as e:
            print(f"[ERROR] Failed to calculate recommended quantity: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_shopping_list_item(self, shopping_list_id: UUID, item: ShoppingListItemCreate, user_id: Optional[UUID] = None) -> dict:
        """Create a new shopping list item"""
        # Validate: either product_id or free_text_name must be set
        if not item.product_id and not item.free_text_name:
            raise ValueError("Either product_id or free_text_name must be provided")
        if item.product_id and item.free_text_name:
            raise ValueError("Cannot set both product_id and free_text_name")
        
        # Calculate recommended quantity if product_id exists and not already provided
        recommended_qty = item.recommended_qty
        unit = item.unit
        
        if item.product_id and user_id and (recommended_qty is None or recommended_qty == 0):
            # Get shopping frequency
            shopping_freq_days = self._get_shopping_frequency_days(user_id)
            
            # Calculate recommended quantity
            calculated_qty = self._calculate_recommended_qty(user_id, item.product_id, shopping_freq_days)
            if calculated_qty:
                recommended_qty = calculated_qty
            
            # Get product unit if not provided
            if not unit:
                try:
                    from app.services.product_service import ProductService
                    product_service = ProductService(self.supabase)
                    product = product_service.get_product(item.product_id)
                    if product:
                        unit = product.get("default_unit", "units")
                except Exception as e:
                    print(f"[WARNING] Could not get product unit: {e}")
                    unit = "units"
        
        data = {
            "shopping_list_id": str(shopping_list_id),
            "product_id": str(item.product_id) if item.product_id else None,
            "free_text_name": item.free_text_name,
            "recommended_qty": recommended_qty,
            "unit": unit or "units",
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
        if item.sufficiency_marked is not None:
            data["sufficiency_marked"] = item.sufficiency_marked
        if item.actual_qty_purchased is not None:
            data["actual_qty_purchased"] = item.actual_qty_purchased
        if item.qty_feedback is not None:
            data["qty_feedback"] = item.qty_feedback
        
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
        log_states = {}  # Map log_id -> state_before_purchase
        
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
            
            # IMPORTANT: Save current state BEFORE updating inventory (needed for predictor)
            current_state_before_update = None
            if existing_inventory.data and len(existing_inventory.data) > 0:
                existing_item = existing_inventory.data[0]
                state_str = existing_item.get("state")
                if state_str:
                    current_state_before_update = InventoryState(state_str)
            
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
            
            # Get feedback from shopping list item
            qty_feedback = item.get("qty_feedback")
            actual_qty = item.get("actual_qty_purchased")
            recommended_qty = item.get("recommended_qty")
            
            # Build note with feedback information
            note_parts = ["Purchased from shopping list"]
            if actual_qty and recommended_qty and actual_qty != recommended_qty:
                note_parts.append(f"Qty: {actual_qty} (recommended: {recommended_qty})")
            if qty_feedback:
                note_parts.append(f"Feedback: {qty_feedback}")
            
            # Create inventory log entry
            log_entry = {
                "user_id": str(user_id),
                "product_id": product_id,
                "action": InventoryAction.PURCHASE.value,
                "delta_state": InventoryState.FULL.value,
                "action_confidence": 1.0,
                "source": InventorySource.SHOPPING_LIST.value,
                "shopping_list_item_id": str(shopping_list_item_id),
                "note": " | ".join(note_parts)
            }
            
            log_result = self.supabase.table("inventory_log").insert(log_entry).execute()
            if log_result.data and len(log_result.data) > 0:
                log_id = log_result.data[0].get("log_id")
                log_ids.append(log_id)
                # Store state before purchase for this log_id
                if current_state_before_update:
                    log_states[log_id] = current_state_before_update
                
                # If there's quantity feedback, create a feedback log entry
                if qty_feedback:
                    # Map shopping feedback to FeedbackKind format that parse_feedback_from_note understands
                    # Format: "MORE", "LESS", "EXACT", "NOT_ENOUGH" -> "MORE", "LESS", "EXACT", "LESS" (stronger)
                    feedback_kind = qty_feedback.upper()
                    if feedback_kind == "NOT_ENOUGH":
                        feedback_kind = "LESS"  # NOT_ENOUGH is treated as LESS (stronger signal)
                    
                    # Create note in format that parse_feedback_from_note can understand
                    # The parser looks for keywords like "MORE", "LESS", "EXACT" in the note
                    feedback_note = f"FEEDBACK: {feedback_kind}"
                    if actual_qty and recommended_qty:
                        feedback_note += f" | Bought {actual_qty}, recommended {recommended_qty}"
                    
                    # Create a feedback log entry that will be processed as FeedbackEvent
                    # Use ADJUST action so it's processed as feedback (not purchase)
                    feedback_log_entry = {
                        "user_id": str(user_id),
                        "product_id": product_id,
                        "action": InventoryAction.ADJUST.value,  # Use ADJUST for feedback
                        "delta_state": None,  # No state change, just feedback
                        "action_confidence": 0.9,
                        "source": InventorySource.SHOPPING_LIST.value,
                        "shopping_list_item_id": str(shopping_list_item_id),
                        "note": feedback_note
                    }
                    
                    feedback_log_result = self.supabase.table("inventory_log").insert(feedback_log_entry).execute()
                    if feedback_log_result.data and len(feedback_log_result.data) > 0:
                        log_ids.append(feedback_log_result.data[0].get("log_id"))
        
        return {
            "shopping_list_id": str(shopping_list_id),
            "status": "COMPLETED",
            "inventory_updates": inventory_updates,
            "log_ids": log_ids,
            "log_states": log_states  # Map log_id -> state_before_purchase
        }

