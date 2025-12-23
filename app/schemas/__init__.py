"""
Pydantic schemas for request/response validation
"""
from app.schemas.product import ProductCategoryCreate, ProductCategoryResponse, ProductCreate, ProductResponse, ProductUpdate
from app.schemas.inventory import InventoryCreate, InventoryResponse, InventoryUpdate, InventoryLogCreate, InventoryLogResponse, ProductActionRequest
from app.schemas.receipt import ReceiptCreate, ReceiptResponse, ReceiptItemCreate, ReceiptItemResponse
from app.schemas.shopping_list import ShoppingListCreate, ShoppingListResponse, ShoppingListUpdate, ShoppingListItemCreate, ShoppingListItemResponse, ShoppingListItemUpdate

__all__ = [
    "ProductCategoryCreate",
    "ProductCategoryResponse",
    "ProductCreate",
    "ProductResponse",
    "ProductUpdate",
    "InventoryCreate",
    "InventoryResponse",
    "InventoryUpdate",
    "InventoryLogCreate",
    "InventoryLogResponse",
    "ProductActionRequest",
    "ReceiptCreate",
    "ReceiptResponse",
    "ReceiptItemCreate",
    "ReceiptItemResponse",
    "ShoppingListCreate",
    "ShoppingListResponse",
    "ShoppingListUpdate",
    "ShoppingListItemCreate",
    "ShoppingListItemResponse",
    "ShoppingListItemUpdate",
]

