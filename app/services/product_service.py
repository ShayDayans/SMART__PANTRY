"""
Product service using Supabase API
"""
from typing import List, Optional
from uuid import UUID
from supabase import Client
from app.schemas.product import ProductCategoryCreate, ProductCreate, ProductUpdate


class ProductService:
    """Service for product operations using Supabase API"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    # Categories
    def get_categories(self) -> List[dict]:
        """Get all product categories"""
        response = self.supabase.table("product_categories").select("*").execute()
        return response.data if response.data else []
    
    def get_category(self, category_id: UUID) -> Optional[dict]:
        """Get a specific category"""
        response = self.supabase.table("product_categories").select("*").eq("category_id", str(category_id)).execute()
        return response.data[0] if response.data else None
    
    def create_category(self, category: ProductCategoryCreate) -> dict:
        """Create a new category"""
        data = {"category_name": category.category_name}
        response = self.supabase.table("product_categories").insert(data).execute()
        return response.data[0] if response.data else {}
    
    def update_category(self, category_id: UUID, category_name: str) -> Optional[dict]:
        """Update a category"""
        response = self.supabase.table("product_categories").update({"category_name": category_name}).eq("category_id", str(category_id)).execute()
        return response.data[0] if response.data else None
    
    def delete_category(self, category_id: UUID) -> bool:
        """Delete a category"""
        response = self.supabase.table("product_categories").delete().eq("category_id", str(category_id)).execute()
        return len(response.data) > 0
    
    # Products
    def get_products(self, category_id: Optional[UUID] = None) -> List[dict]:
        """Get all products, optionally filtered by category"""
        query = self.supabase.table("products").select("*, product_categories(*)")
        if category_id:
            query = query.eq("category_id", str(category_id))
        response = query.execute()
        return response.data if response.data else []
    
    def get_product(self, product_id: UUID) -> Optional[dict]:
        """Get a specific product"""
        response = self.supabase.table("products").select("*, product_categories(*)").eq("product_id", str(product_id)).execute()
        return response.data[0] if response.data else None
    
    def create_product(self, product: ProductCreate) -> dict:
        """Create a new product"""
        data = {
            "product_name": product.product_name,
            "barcode": product.barcode,
            "category_id": str(product.category_id) if product.category_id else None,
            "default_unit": product.default_unit,
        }
        response = self.supabase.table("products").insert(data).execute()
        return response.data[0] if response.data else {}
    
    def update_product(self, product_id: UUID, product: ProductUpdate) -> Optional[dict]:
        """Update a product"""
        data = {}
        if product.product_name is not None:
            data["product_name"] = product.product_name
        if product.barcode is not None:
            data["barcode"] = product.barcode
        if product.category_id is not None:
            data["category_id"] = str(product.category_id)
        if product.default_unit is not None:
            data["default_unit"] = product.default_unit
        
        if not data:
            return None
        
        response = self.supabase.table("products").update(data).eq("product_id", str(product_id)).execute()
        return response.data[0] if response.data else None
    
    def delete_product(self, product_id: UUID) -> bool:
        """Delete a product"""
        response = self.supabase.table("products").delete().eq("product_id", str(product_id)).execute()
        return len(response.data) > 0

