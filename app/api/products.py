"""
Products API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
from supabase import Client

from app.db.supabase_client import get_supabase
from app.services.product_service import ProductService
from app.schemas.product import (
    ProductCategoryCreate, ProductCategoryResponse,
    ProductCreate, ProductResponse, ProductUpdate
)

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(supabase: Client = Depends(get_supabase)) -> ProductService:
    """Dependency to get product service"""
    return ProductService(supabase)


# Categories
@router.get("/categories", response_model=List[ProductCategoryResponse])
def get_categories(service: ProductService = Depends(get_product_service)):
    """Get all product categories"""
    categories = service.get_categories()
    return categories


@router.get("/categories/{category_id}", response_model=ProductCategoryResponse)
def get_category(
    category_id: UUID,
    service: ProductService = Depends(get_product_service)
):
    """Get a specific category"""
    category = service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/categories", response_model=ProductCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: ProductCategoryCreate,
    service: ProductService = Depends(get_product_service)
):
    """Create a new category"""
    new_category = service.create_category(category)
    return new_category


@router.put("/categories/{category_id}", response_model=ProductCategoryResponse)
def update_category(
    category_id: UUID,
    category_name: str,
    service: ProductService = Depends(get_product_service)
):
    """Update a category"""
    category = service.update_category(category_id, category_name)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    service: ProductService = Depends(get_product_service)
):
    """Delete a category"""
    deleted = service.delete_category(category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")


# Products
@router.get("", response_model=List[ProductResponse])
def get_products(
    category_id: Optional[UUID] = None,
    service: ProductService = Depends(get_product_service)
):
    """Get all products, optionally filtered by category"""
    products = service.get_products(category_id)
    return products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    service: ProductService = Depends(get_product_service)
):
    """Get a specific product"""
    product = service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    """Create a new product"""
    new_product = service.create_product(product)
    return new_product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    product: ProductUpdate,
    service: ProductService = Depends(get_product_service)
):
    """Update a product"""
    updated_product = service.update_product(product_id, product)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated_product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: UUID,
    service: ProductService = Depends(get_product_service)
):
    """Delete a product"""
    deleted = service.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")

