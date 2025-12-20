"""
Receipts API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
from app.core.config import settings
from app.services.receipt_service import ReceiptService
from app.services.receipt_processing_service import ReceiptProcessingService
from app.schemas.receipt import ReceiptCreate, ReceiptResponse

router = APIRouter(prefix="/receipts", tags=["receipts"])


def get_receipt_service(supabase: Client = Depends(get_supabase)) -> ReceiptService:
    """Dependency to get receipt service"""
    return ReceiptService(supabase)


def get_receipt_processing_service(supabase: Client = Depends(get_supabase)) -> ReceiptProcessingService:
    """Dependency to get receipt processing service"""
    openai_api_key = settings.openai_api_key
    if not openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key is not configured. Please set OPENAI_API_KEY in your .env file or environment variables."
        )
    return ReceiptProcessingService(supabase, openai_api_key)


@router.get("", response_model=List[ReceiptResponse])
def get_receipts(
    user_id: UUID,
    limit: int = 100,
    service: ReceiptService = Depends(get_receipt_service)
):
    """Get all receipts for a user"""
    receipts = service.get_receipts(user_id, limit)
    return receipts


@router.get("/{receipt_id}", response_model=ReceiptResponse)
def get_receipt(
    receipt_id: UUID,
    service: ReceiptService = Depends(get_receipt_service)
):
    """Get a specific receipt with items"""
    receipt = service.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


@router.post("", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
def create_receipt(
    user_id: UUID,
    receipt: ReceiptCreate,
    service: ReceiptService = Depends(get_receipt_service)
):
    """Create a new receipt with items"""
    new_receipt = service.create_receipt(user_id, receipt)
    return new_receipt


@router.put("/{receipt_id}", response_model=ReceiptResponse)
def update_receipt(
    receipt_id: UUID,
    receipt_data: dict,
    service: ReceiptService = Depends(get_receipt_service)
):
    """Update a receipt"""
    receipt = service.update_receipt(receipt_id, receipt_data)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(
    receipt_id: UUID,
    service: ReceiptService = Depends(get_receipt_service)
):
    """Delete a receipt"""
    deleted = service.delete_receipt(receipt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Receipt not found")


@router.post("/scan")
async def scan_receipt(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    processing_service: ReceiptProcessingService = Depends(get_receipt_processing_service)
):
    """
    Scan receipt image with AI, match products, and return for user confirmation.
    Does NOT add to inventory yet - that's done in /confirm endpoint.
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file data
        file_data = await file.read()
        
        # Process receipt (scan + match, but don't add to inventory yet)
        result = processing_service.scan_and_match_receipt(
            user_id=UUID(user_id),
            image_data=file_data,
            file_name=file.filename,
            content_type=file.content_type
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan receipt: {str(e)}")


@router.post("/{receipt_id}/confirm")
def confirm_receipt_and_add_to_inventory(
    receipt_id: str,
    user_id: UUID,
    confirmed_items: List[dict],
    processing_service: ReceiptProcessingService = Depends(get_receipt_processing_service)
):
    """
    After user confirms the matched products, add them to inventory as FULL
    and create inventory logs.
    
    Body format:
    {
        "user_id": "uuid",
        "confirmed_items": [
            {
                "product_id": "uuid",
                "quantity": 2.0,
                "unit_price": 10.5,
                "total_price": 21.0,
                "detected_name": "Milk",
                "confidence": 0.95
            }
        ]
    }
    """
    try:
        result = processing_service.confirm_and_add_to_inventory(
            user_id=user_id,
            receipt_id=receipt_id,
            confirmed_items=confirmed_items
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add items to inventory: {str(e)}")

