"""
Receipt service using Supabase API
"""
from typing import List, Optional
from uuid import UUID
from supabase import Client
from app.schemas.receipt import ReceiptCreate, ReceiptItemCreate


class ReceiptService:
    """Service for receipt operations using Supabase API"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def get_receipts(self, user_id: UUID, limit: int = 100) -> List[dict]:
        """Get all receipts for a user"""
        response = self.supabase.table("receipts").select("*, receipt_items(*)").eq("user_id", str(user_id)).order("purchased_at", desc=True).limit(limit).execute()
        return response.data if response.data else []
    
    def get_receipt(self, receipt_id: UUID) -> Optional[dict]:
        """Get a specific receipt with items"""
        response = self.supabase.table("receipts").select("*, receipt_items(*)").eq("receipt_id", str(receipt_id)).execute()
        return response.data[0] if response.data else None
    
    def create_receipt(self, user_id: UUID, receipt: ReceiptCreate) -> dict:
        """Create a new receipt with items"""
        receipt_data = {
            "user_id": str(user_id),
            "store_name": receipt.store_name,
            "purchased_at": receipt.purchased_at.isoformat() if receipt.purchased_at else None,
            "total_amount": float(receipt.total_amount) if receipt.total_amount else None,
            "raw_text": receipt.raw_text,
        }
        
        # Insert receipt
        receipt_response = self.supabase.table("receipts").insert(receipt_data).execute()
        receipt_id = receipt_response.data[0]["receipt_id"] if receipt_response.data else None
        
        if not receipt_id:
            raise ValueError("Failed to create receipt")
        
        # Insert items if provided
        if receipt.items:
            items_data = []
            for item in receipt.items:
                item_data = {
                    "receipt_id": receipt_id,
                    "line_index": item.line_index,
                    "raw_label": item.raw_label,
                    "normalized_label": item.normalized_label,
                    "product_id": str(item.product_id) if item.product_id else None,
                    "match_confidence": item.match_confidence,
                    "quantity": float(item.quantity) if item.quantity else None,
                    "unit": item.unit,
                    "unit_price": float(item.unit_price) if item.unit_price else None,
                    "total_price": float(item.total_price) if item.total_price else None,
                }
                items_data.append(item_data)
            
            self.supabase.table("receipt_items").insert(items_data).execute()
        
        # Fetch complete receipt with items
        return self.get_receipt(UUID(receipt_id))
    
    def create_receipt_item(self, receipt_id: str, item_data: dict) -> dict:
        """Create a single receipt item"""
        receipt_item_data = {
            "receipt_id": receipt_id,
            "product_id": str(item_data.get("product_id")) if item_data.get("product_id") else None,
            "raw_label": item_data.get("detected_name", item_data.get("raw_label", "")),
            "normalized_label": item_data.get("detected_name", item_data.get("normalized_label")),
            "quantity": float(item_data.get("quantity", 1.0)) if item_data.get("quantity") else None,
            "unit": item_data.get("unit", "units"),
            "unit_price": float(item_data.get("unit_price")) if item_data.get("unit_price") else None,
            "total_price": float(item_data.get("total_price")) if item_data.get("total_price") else None,
            "match_confidence": item_data.get("confidence", item_data.get("match_confidence", 0.9))
        }
        
        response = self.supabase.table("receipt_items").insert(receipt_item_data).execute()
        return response.data[0] if response.data else {}
    
    def update_receipt(self, receipt_id: UUID, receipt_data: dict) -> Optional[dict]:
        """Update a receipt"""
        data = {}
        if "store_name" in receipt_data:
            data["store_name"] = receipt_data["store_name"]
        if "purchased_at" in receipt_data:
            data["purchased_at"] = receipt_data["purchased_at"]
        if "total_amount" in receipt_data:
            data["total_amount"] = receipt_data["total_amount"]
        if "raw_text" in receipt_data:
            data["raw_text"] = receipt_data["raw_text"]
        
        if not data:
            return None
        
        response = self.supabase.table("receipts").update(data).eq("receipt_id", str(receipt_id)).execute()
        return response.data[0] if response.data else None
    
    def delete_receipt(self, receipt_id: UUID) -> bool:
        """Delete a receipt (cascade deletes items)"""
        response = self.supabase.table("receipts").delete().eq("receipt_id", str(receipt_id)).execute()
        return len(response.data) > 0

