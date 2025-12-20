"""
Product and Category schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class ProductCategoryCreate(BaseModel):
    category_name: str = Field(..., description="Name of the category")


class ProductCategoryResponse(BaseModel):
    category_id: UUID
    category_name: str
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    product_name: str = Field(..., description="Name of the product")
    barcode: Optional[str] = Field(None, description="Product barcode")
    category_id: Optional[UUID] = Field(None, description="Category ID")
    default_unit: Optional[str] = Field(None, description="Default unit (e.g., 'g', 'ml', 'unit')")


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    barcode: Optional[str] = None
    category_id: Optional[UUID] = None
    default_unit: Optional[str] = None


class ProductResponse(BaseModel):
    product_id: UUID
    product_name: str
    barcode: Optional[str] = None
    category_id: Optional[UUID] = None
    default_unit: Optional[str] = None
    category: Optional[ProductCategoryResponse] = None
    
    class Config:
        from_attributes = True

