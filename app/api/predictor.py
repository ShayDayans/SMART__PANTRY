"""
Predictor API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
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
    user_id: UUID,
    log_id: UUID,
    service: PredictorService = Depends(get_predictor_service)
):
    """Process an inventory log event and update predictions"""
    try:
        service.process_inventory_log(str(log_id))
        return {"message": "Log processed successfully", "log_id": str(log_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh/{user_id}")
def refresh_predictions(
    user_id: UUID,
    service: PredictorService = Depends(get_predictor_service)
):
    """Refresh predictions for all products in user's inventory"""
    try:
        service.refresh_user_inventory_forecasts(str(user_id))
        return {"message": "Predictions refreshed successfully", "user_id": str(user_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/forecast/{user_id}/{product_id}")
def get_product_forecast(
    user_id: UUID,
    product_id: UUID,
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

