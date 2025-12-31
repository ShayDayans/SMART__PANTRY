"""
AI-powered receipt scanning service using OpenAI Vision API
"""
from typing import List, Optional
import os
import json
from openai import OpenAI


class ReceiptItem:
    """Represents an item found in a receipt"""
    def __init__(
        self, 
        name: str, 
        quantity: float = 1.0,
        unit_price: Optional[float] = None,
        total_price: Optional[float] = None,
        category: Optional[str] = None,
        confidence: float = 0.8
    ):
        self.name = name
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_price = total_price
        self.category = category
        self.confidence = confidence
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "category": self.category,
            "confidence": self.confidence
        }


class ReceiptScanResult:
    """Complete result of receipt scanning"""
    def __init__(
        self,
        items: List[ReceiptItem],
        store_name: Optional[str] = None,
        purchase_date: Optional[str] = None,
        total_amount: Optional[float] = None,
        raw_text: Optional[str] = None
    ):
        self.items = items
        self.store_name = store_name
        self.purchase_date = purchase_date
        self.total_amount = total_amount
        self.raw_text = raw_text
    
    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "store_name": self.store_name,
            "purchase_date": self.purchase_date,
            "total_amount": self.total_amount,
            "raw_text": self.raw_text
        }


class ReceiptScannerService:
    """Service for scanning and analyzing receipts using AI"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error initializing OpenAI client: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def scan_receipt_from_url(self, image_url: str) -> ReceiptScanResult:
        """
        Scan receipt from image URL using OpenAI Vision API
        """
        try:
            # Call OpenAI Vision API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert receipt analyzer. Extract ALL items from the receipt image with high accuracy.
                        
Return ONLY a valid JSON object (no markdown, no code blocks) with this exact structure:
{
  "store_name": "Store Name or null",
  "purchase_date": "YYYY-MM-DD or null",
  "total_amount": numeric_value_or_null,
  "items": [
    {
      "name": "Product Name in English",
      "quantity": 1.0,
      "unit_price": 10.50,
      "total_price": 10.50,
      "category": "Dairy/Bread/Meat/Vegetables/Fruits/Beverages/Snacks/Other or null",
      "confidence": 0.95
    }
  ]
}

Rules:
- Extract EVERY product line item
- Translate Hebrew product names to English
- Infer reasonable categories based on product names
- Set confidence: 0.9-1.0 for clear items, 0.6-0.8 for unclear
- Skip non-product lines (tax, total, discounts)
- Return ONLY the JSON, no other text"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all items from this receipt image. Return pure JSON only."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse response
            content = response.choices[0].message.content
            print(f"OpenAI Response: {content}")
            
            # Clean up markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            data = json.loads(content)
            
            # Convert to ReceiptScanResult
            items = []
            for item_data in data.get("items", []):
                items.append(ReceiptItem(
                    name=item_data["name"],
                    quantity=float(item_data.get("quantity", 1.0)),
                    unit_price=float(item_data["unit_price"]) if item_data.get("unit_price") else None,
                    total_price=float(item_data["total_price"]) if item_data.get("total_price") else None,
                    category=item_data.get("category"),
                    confidence=float(item_data.get("confidence", 0.8))
                ))
            
            return ReceiptScanResult(
                items=items,
                store_name=data.get("store_name"),
                purchase_date=data.get("purchase_date"),
                total_amount=float(data["total_amount"]) if data.get("total_amount") else None,
                raw_text=content
            )
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw content: {content}")
            raise Exception(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            print(f"Error scanning receipt: {e}")
            raise Exception(f"Failed to scan receipt: {str(e)}")
