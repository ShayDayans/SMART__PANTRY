"""
Receipt schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class ReceiptItemCreate(BaseModel):
    line_index: Optional[int] = Field(None, description="Line order in receipt")
    raw_label: str = Field(..., description="Raw label from receipt")
    normalized_label: Optional[str] = Field(None, description="Normalized label")
    product_id: Optional[UUID] = Field(None, description="Matched product ID")
    match_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Match confidence")
    quantity: Optional[Decimal] = Field(None, description="Quantity")
    unit: Optional[str] = Field(None, description="Unit")
    unit_price: Optional[Decimal] = Field(None, description="Unit price")
    total_price: Optional[Decimal] = Field(None, description="Total price")


class ReceiptItemResponse(BaseModel):
    receipt_item_id: UUID
    receipt_id: UUID
    line_index: Optional[int] = None
    raw_label: str
    normalized_label: Optional[str] = None
    product_id: Optional[UUID] = None
    match_confidence: Optional[float] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReceiptCreate(BaseModel):
    store_name: Optional[str] = Field(None, description="Store name")
    purchased_at: Optional[datetime] = Field(None, description="Purchase timestamp")
    total_amount: Optional[Decimal] = Field(None, description="Total amount")
    raw_text: Optional[str] = Field(None, description="Raw OCR text")
    items: Optional[List[ReceiptItemCreate]] = Field(default_factory=list, description="Receipt items")


class ReceiptResponse(BaseModel):
    receipt_id: UUID
    user_id: UUID
    store_name: Optional[str] = None
    purchased_at: Optional[datetime] = None
    total_amount: Optional[float] = None
    raw_text: Optional[str] = None
    created_at: datetime
    items: Optional[List[ReceiptItemResponse]] = None
    
    class Config:
        from_attributes = True

