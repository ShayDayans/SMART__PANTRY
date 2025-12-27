"""
Predictor API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
from app.core.dependencies import get_current_user_id
from app.services.predictor_service import PredictorService

router = APIRouter(prefix="/predictor", tags=["predictor"])


def get_predictor_service(supabase: Client = Depends(get_supabase)) -> PredictorService:
    """Dependency to get predictor service"""
    try:
        return PredictorService(supabase)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/process-log/{log_id}")
def process_inventory_log(
    log_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: PredictorService = Depends(get_predictor_service)
):
    """Process an inventory log event and update predictions"""
    try:
        service.process_inventory_log(str(log_id))
        return {"message": "Log processed successfully", "log_id": str(log_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh")
def refresh_predictions(
    user_id: UUID = Depends(get_current_user_id),
    service: PredictorService = Depends(get_predictor_service)
):
    """Refresh predictions for all products in user's inventory"""
    try:
        service.refresh_user_inventory_forecasts(str(user_id))
        return {"message": "Predictions refreshed successfully", "user_id": str(user_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/forecast/{product_id}")
def get_product_forecast(
    product_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
):
    """Get the latest forecast for a specific product"""
    try:
        # Get the latest forecast from inventory_forecasts table
        response = supabase.table("inventory_forecasts").select("*").eq(
            "user_id", str(user_id)
        ).eq(
            "product_id", str(product_id)
        ).order("generated_at", desc=True).limit(1).execute()
        
        if response.data and len(response.data) > 0:
            forecast = response.data[0]
            return {
                "forecast_id": forecast.get("forecast_id"),
                "expected_days_left": forecast.get("expected_days_left"),
                "predicted_state": forecast.get("predicted_state"),
                "confidence": forecast.get("confidence"),
                "generated_at": forecast.get("generated_at")
            }
        else:
            # No forecast found, return default
            return {
                "expected_days_left": 0,
                "predicted_state": "UNKNOWN",
                "confidence": 0.0,
                "generated_at": None
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get forecast: {str(e)}")


@router.post("/learn-from-shopping-feedback")
def learn_from_shopping_feedback(
    request: dict,  # {"shopping_list_item_id": UUID, "feedback": "MORE" | "LESS"}
    user_id: UUID = Depends(get_current_user_id),
    service: PredictorService = Depends(get_predictor_service),
    supabase: Client = Depends(get_supabase)
):
    """
    Store shopping list feedback for weekly model update.
    
    NOTE: This does NOT update the model immediately.
    The feedback is stored and will be processed during the weekly update.
    
    Feedback types:
    - "MORE": The purchased quantity will last MORE days than predicted (consumption is slower)
    - "LESS": The purchased quantity will last LESS days than predicted (consumption is faster)
    
    The actual model update happens during weekly_model_update() which:
    - Only updates products whose cycle should have ended (days_since_purchase >= cycle_mean_days)
    - Processes all accumulated feedback at once
    """
    from app.models.enums import InventoryAction, InventorySource
    from app.services.inventory_service import InventoryService
    from app.schemas.inventory import InventoryLogCreate
    
    try:
        shopping_list_item_id = request.get("shopping_list_item_id")
        feedback = request.get("feedback")
        
        if not shopping_list_item_id or not feedback:
            raise HTTPException(status_code=400, detail="Missing shopping_list_item_id or feedback")
        
        # Get shopping list item to find product_id
        item_result = supabase.table("shopping_list_items").select("product_id").eq(
            "shopping_list_item_id", str(shopping_list_item_id)
        ).execute()
        
        if not item_result.data or not item_result.data[0].get("product_id"):
            raise HTTPException(status_code=404, detail="Shopping list item not found or has no product_id")
        
        product_id = item_result.data[0]["product_id"]
        feedback_kind = feedback.upper()
        
        if feedback_kind not in ("MORE", "LESS"):
            raise HTTPException(status_code=400, detail="Feedback must be 'MORE' or 'LESS'")
        
        # Update days_left immediately (but NOT cycle_mean_days)
        # cycle_mean_days will be updated only during weekly update based on observed cycle length
        from datetime import datetime, timezone
        from app.models.enums import InventoryState, InventorySource
        now = datetime.now(timezone.utc)
        
        # Get current state to calculate new days_left
        try:
            predictor_profile_id, cfg = service._load_cfg_and_profile(str(user_id))
            products = dict(service.repo.get_user_inventory_products(str(user_id)))
            category_id = products.get(str(product_id))
            state = service._load_or_init_state(
                str(user_id), str(product_id), predictor_profile_id, cfg, category_id, now
            )
            
            # Get current days_left from inventory (if user has updated it)
            from app.services.inventory_service import InventoryService
            inventory_service = InventoryService(supabase)
            current_item = inventory_service.get_inventory_item(user_id, UUID(product_id))
            current_days_left = current_item.get("estimated_qty") if current_item else None
            if current_days_left is not None:
                try:
                    current_days_left = float(current_days_left)
                except (ValueError, TypeError):
                    current_days_left = None
            
            from ema_cycle_predictor import compute_days_left, predict, derive_state
            mult = service.repo.get_active_habit_multiplier(str(user_id), str(product_id), category_id, now)
            # Use inventory_days_left if available, otherwise calculate from cycle_mean_days
            current_days_left = compute_days_left(state, now, mult, cfg, inventory_days_left=current_days_left)
            cycle_mean_days_before = state.cycle_mean_days
            
            # Check if product is EMPTY (days_left = 0 or very close to 0)
            is_empty = current_days_left <= 0.01 or (current_item and current_item.get("state") == "EMPTY")
            
            # Apply percentage multiplier to days_left (NOT to cycle_mean_days)
            if is_empty:
                # Special handling for EMPTY products
                if feedback_kind == "MORE":
                    # If EMPTY and MORE: increase moderately by 0.15 * cycle_mean_days
                    # This means the user is indicating they have the product again
                    if state.cycle_mean_days > 0:
                        # Moderate increase: 15% of the mean (not 115%!)
                        new_days_left = state.cycle_mean_days * 0.15
                    else:
                        # If no cycle_mean_days yet, start with a small value (1-2 days)
                        new_days_left = 1.5
                    print(f"[EMPTY->MORE] Moderate increase for product {product_id}: days_left = {new_days_left} (from cycle_mean_days = {state.cycle_mean_days})")
                else:  # LESS
                    # If EMPTY and LESS: stay at 0 (or very small value)
                    new_days_left = 0.0
                    print(f"[EMPTY->LESS] Product {product_id} stays EMPTY")
            else:
                # Normal case: product has days_left > 0
                if feedback_kind == "MORE":
                    multiplier = 1.15  # 15% more days
                else:  # LESS
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
            params_json = service._make_json_serializable(params_json)
            service.repo.upsert_predictor_state(
                user_id=str(user_id),
                product_id=str(product_id),
                predictor_profile_id=predictor_profile_id,
                params=params_json,
                confidence=confidence,
                updated_at=now,
            )
            
            # Update inventory with new days_left (but keep cycle_mean_days unchanged)
            print(f"[DEBUG learn_from_shopping_feedback] Updating inventory: user_id={user_id}, product_id={product_id}, new_days_left={new_days_left}, new_state={new_state.value}, confidence={confidence}")
            try:
                service.repo.upsert_inventory_days_estimate(
                    user_id=str(user_id),
                    product_id=str(product_id),
                    days_left=new_days_left,
                    state=InventoryState(new_state.value),
                    confidence=confidence,
                    source=InventorySource.SHOPPING_LIST,
                )
                print(f"[DEBUG learn_from_shopping_feedback] Successfully updated inventory")
            except Exception as e:
                print(f"[ERROR learn_from_shopping_feedback] Failed to update inventory: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"Warning: Could not update days_left: {e}")
            current_days_left = 0.0
            cycle_mean_days_before = 0.0
            new_days_left = 0.0
        
        # Log feedback to shopping_feedback_log table
        try:
            supabase.table("shopping_feedback_log").insert({
                "shopping_list_item_id": str(shopping_list_item_id),
                "product_id": str(product_id),
                "user_id": str(user_id),
                "feedback_type": feedback_kind,
                "predicted_days_before": float(current_days_left),
                "predicted_days_after": float(new_days_left) if 'new_days_left' in locals() else None,
                "cycle_mean_days_before": float(cycle_mean_days_before),
                "cycle_mean_days_after": float(cycle_mean_days_before),  # cycle_mean_days doesn't change immediately
                "created_at": now.isoformat()
            }).execute()
        except Exception as e:
            print(f"Warning: Could not log to shopping_feedback_log: {e}")
        
        # Also create inventory_log entry for tracking (but don't process it)
        feedback_note = f"FEEDBACK: {feedback_kind} | Shopping list feedback: quantity will last {'more' if feedback_kind == 'MORE' else 'less'} days than predicted (stored for weekly update)"
        
        inventory_service = InventoryService(supabase)
        log_create = InventoryLogCreate(
            product_id=UUID(product_id),
            action=InventoryAction.ADJUST,
            delta_state=None,
            action_confidence=0.9,
            source=InventorySource.SHOPPING_LIST,
            shopping_list_item_id=UUID(shopping_list_item_id),
            note=feedback_note
        )
        
        log_entry = inventory_service.create_inventory_log(user_id=user_id, log=log_create)
        
        # NOTE: We do NOT call process_inventory_log here!
        # The feedback will be processed during weekly_model_update()
        
        return {
            "message": f"Days left updated: {feedback_kind} feedback applied (cycle_mean_days unchanged until weekly update)",
            "log_id": str(log_entry.get("log_id")) if log_entry else None,
            "product_id": product_id,
            "days_left_before": float(current_days_left) if 'current_days_left' in locals() else None,
            "days_left_after": float(new_days_left) if 'new_days_left' in locals() else None,
            "cycle_mean_days": float(cycle_mean_days_before) if 'cycle_mean_days_before' in locals() else None,
            "note": "cycle_mean_days will be updated during weekly update based on observed cycle length"
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process feedback: {str(e)}")


@router.post("/weekly-update")
def weekly_model_update(
    user_id: UUID = Depends(get_current_user_id),
    service: PredictorService = Depends(get_predictor_service)
):
    """
    Run weekly model update for all user's products.
    This should be called by a background task/scheduler weekly.
    Only updates products whose cycle should have ended (days_since_purchase >= cycle_mean_days).
    """
    try:
        service.weekly_model_update_all_products(str(user_id))
        return {
            "message": "Weekly model update completed",
            "user_id": str(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to run weekly update: {str(e)}")

