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
    Learn from shopping list feedback about days prediction.
    
    Feedback types:
    - "MORE": The purchased quantity will last MORE days than predicted (consumption is slower)
    - "LESS": The purchased quantity will last LESS days than predicted (consumption is faster)
    
    This creates a feedback log entry that updates the model's cycle_mean_days:
    - MORE: Increases cycle_mean_days by 15% of last_pred_days_left (max 3 days)
    - LESS: Decreases cycle_mean_days by 15% of last_pred_days_left (max 3 days)
    
    The update uses alpha_weak (0.10) for smooth adaptation.
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
        
        # Create feedback log entry
        feedback_note = f"FEEDBACK: {feedback_kind} | Shopping list feedback: quantity will last {'more' if feedback_kind == 'MORE' else 'less'} days than predicted"
        
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
        
        # Process the log to update the model
        if log_entry and log_entry.get("log_id"):
            service.process_inventory_log(str(log_entry["log_id"]))
            return {
                "message": f"Model updated: {feedback_kind} feedback applied",
                "log_id": str(log_entry["log_id"]),
                "product_id": product_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create feedback log entry")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process feedback: {str(e)}")

