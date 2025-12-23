"""
Shopping list schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.enums import ShoppingListStatus, ShoppingItemStatus, ItemAddedBy


class ShoppingListCreate(BaseModel):
    title: Optional[str] = Field(None, description="List title")
    status: ShoppingListStatus = Field(ShoppingListStatus.ACTIVE, description="List status")
    notes: Optional[str] = Field(None, description="Optional notes")


class ShoppingListUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[ShoppingListStatus] = None
    notes: Optional[str] = None


class ShoppingListResponse(BaseModel):
    shopping_list_id: UUID
    user_id: UUID
    title: Optional[str] = None
    status: str
    created_at: datetime
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class ShoppingListItemCreate(BaseModel):
    product_id: Optional[UUID] = Field(None, description="Product ID (if linked to product)")
    free_text_name: Optional[str] = Field(None, description="Free text name (if not linked)")
    recommended_qty: Optional[float] = Field(None, description="Recommended quantity")
    unit: Optional[str] = Field(None, description="Unit")
    user_qty_override: Optional[float] = Field(None, description="User quantity override")
    status: ShoppingItemStatus = Field(ShoppingItemStatus.PLANNED, description="Item status")
    priority: Optional[int] = Field(None, description="Priority")
    added_by: ItemAddedBy = Field(ItemAddedBy.USER, description="Who added the item")


class ShoppingListItemUpdate(BaseModel):
    product_id: Optional[UUID] = None
    free_text_name: Optional[str] = None
    recommended_qty: Optional[float] = None
    unit: Optional[str] = None
    user_qty_override: Optional[float] = None
    status: Optional[ShoppingItemStatus] = None
    priority: Optional[int] = None
    sufficiency_marked: Optional[bool] = Field(None, description="User marked if quantity is sufficient")
    actual_qty_purchased: Optional[float] = Field(None, description="Actual quantity purchased")
    qty_feedback: Optional[str] = Field(None, description="Feedback: LESS, MORE, EXACT, NOT_ENOUGH")


class ShoppingListItemResponse(BaseModel):
    shopping_list_item_id: UUID
    shopping_list_id: UUID
    product_id: Optional[UUID] = None
    free_text_name: Optional[str] = None
    recommended_qty: Optional[float] = None
    unit: Optional[str] = None
    user_qty_override: Optional[float] = None
    status: str
    priority: Optional[int] = None
    added_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

