"""
Inventory schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.enums import InventoryState, InventorySource, InventoryAction


class InventoryCreate(BaseModel):
    product_id: UUID = Field(..., description="Product ID")
    state: InventoryState = Field(InventoryState.UNKNOWN, description="Inventory state")
    estimated_qty: Optional[float] = Field(None, description="Estimated quantity")
    qty_unit: Optional[str] = Field(None, description="Quantity unit")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence level")
    last_source: InventorySource = Field(InventorySource.SYSTEM, description="Source of update")
    displayed_name: Optional[str] = Field(None, description="Display name for UI")


class InventoryUpdate(BaseModel):
    state: Optional[InventoryState] = None
    estimated_qty: Optional[float] = None
    qty_unit: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    last_source: Optional[InventorySource] = None
    displayed_name: Optional[str] = None


class InventoryResponse(BaseModel):
    user_id: UUID
    product_id: UUID
    state: str
    estimated_qty: Optional[float] = None
    qty_unit: Optional[str] = None
    confidence: float
    last_updated_at: datetime
    last_source: str
    displayed_name: Optional[str] = None
    # Include nested products data
    products: Optional[dict] = None
    
    class Config:
        from_attributes = True
        # Allow extra fields to preserve nested products structure
        extra = "allow"


class InventoryLogCreate(BaseModel):
    product_id: UUID = Field(..., description="Product ID")
    action: InventoryAction = Field(..., description="Action type")
    delta_state: Optional[InventoryState] = Field(None, description="State change")
    action_confidence: float = Field(1.0, ge=0.0, le=1.0, description="Action confidence")
    source: InventorySource = Field(InventorySource.SYSTEM, description="Source of action")
    receipt_item_id: Optional[UUID] = Field(None, description="Related receipt item ID")
    shopping_list_item_id: Optional[UUID] = Field(None, description="Related shopping list item ID")
    note: Optional[str] = Field(None, description="Optional note")


class InventoryLogResponse(BaseModel):
    log_id: UUID
    user_id: UUID
    product_id: UUID
    action: str
    delta_state: Optional[str] = None
    action_confidence: float
    occurred_at: datetime
    source: str
    receipt_item_id: Optional[UUID] = None
    shopping_list_item_id: Optional[UUID] = None
    note: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProductActionRequest(BaseModel):
    """Schema for product action (thrown away, repurchased, ran out)"""
    action_type: str = Field(..., description="Action type: 'thrown_away', 'repurchased', or 'ran_out'")
    reason: str = Field(..., description="Selected reason from predefined options")
    custom_reason: Optional[str] = Field(None, description="Custom reason if 'other' was selected")
