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
        # Handle category_id - check if it was explicitly provided (even if None)
        # We need to check if the field was set in the Pydantic model
        if hasattr(product, '__fields_set__') and 'category_id' in product.__fields_set__:
            # category_id was explicitly provided in the request
            print(f"[DEBUG ProductService] category_id is in __fields_set__, value: {product.category_id}")
            if product.category_id is not None:
                data["category_id"] = str(product.category_id)
            else:
                # Explicitly set to None to remove category
                data["category_id"] = None
                print(f"[DEBUG ProductService] Setting category_id to None to remove category")
        elif product.category_id is not None:
            # Fallback: if category_id is not None, set it
            print(f"[DEBUG ProductService] category_id not in __fields_set__, but value is not None: {product.category_id}")
            data["category_id"] = str(product.category_id)
        else:
            print(f"[DEBUG ProductService] category_id not in __fields_set__ and value is None - skipping")
        if product.default_unit is not None:
            data["default_unit"] = product.default_unit
        
        if not data:
            print(f"[DEBUG ProductService] No data to update, returning None")
            return None
        
        print(f"[DEBUG ProductService] Updating product {product_id} with data: {data}")
        try:
            # Verify product exists first
            check_response = self.supabase.table("products").select("product_id").eq("product_id", str(product_id)).execute()
            if not check_response.data:
                print(f"[ERROR ProductService] Product {product_id} not found in database!")
                return None
            
            # Update the product in the products table
            response = self.supabase.table("products").update(data).eq("product_id", str(product_id)).execute()
            print(f"[DEBUG ProductService] Update response: {response.data}")
            
            if not response.data:
                print(f"[ERROR ProductService] Update returned no data!")
                return None
            
            # After update, fetch the product again with category information
            # This ensures we return the full product with category details
            updated_product = response.data[0]
            print(f"[DEBUG ProductService] Successfully updated product: product_id={updated_product.get('product_id')}, category_id={updated_product.get('category_id')}")
            
            # Fetch the product with category join to return complete data
            full_product = self.get_product(product_id)
            if full_product:
                print(f"[DEBUG ProductService] Fetched full product with category: {full_product.get('product_categories')}")
                return full_product
            else:
                # Fallback to updated product if get_product fails
                print(f"[WARNING ProductService] Could not fetch full product, returning updated product")
                return updated_product
        except Exception as e:
            print(f"[ERROR ProductService] Error updating product: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def delete_product(self, product_id: UUID) -> bool:
        """Delete a product"""
        response = self.supabase.table("products").delete().eq("product_id", str(product_id)).execute()
        return len(response.data) > 0

