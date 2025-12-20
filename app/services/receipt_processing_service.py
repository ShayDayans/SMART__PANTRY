"""
Receipt processing service - orchestrates receipt scanning, product matching, and storage
"""
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
from supabase import Client
from difflib import SequenceMatcher

from app.services.storage_service import StorageService
from app.services.receipt_scanner_service import ReceiptScannerService, ReceiptScanResult
from app.services.product_service import ProductService
from app.services.receipt_service import ReceiptService
from app.schemas.product import ProductCreate, ProductCategoryCreate
from app.schemas.receipt import ReceiptCreate


class ReceiptProcessingService:
    """
    Main service for processing receipts end-to-end:
    1. Upload image to storage
    2. Scan with AI
    3. Match products (or create new ones)
    4. Return matched items for user confirmation
    5. After confirmation - add to inventory with logging
    """
    
    def __init__(self, supabase: Client, openai_api_key: Optional[str] = None):
        self.supabase = supabase
        self.storage_service = StorageService(supabase)
        self.scanner_service = ReceiptScannerService(openai_api_key)
        self.product_service = ProductService(supabase)
        self.receipt_service = ReceiptService(supabase)
    
    def scan_and_match_receipt(
        self,
        user_id: UUID,
        image_data: bytes,
        file_name: str,
        content_type: str = "image/jpeg"
    ) -> dict:
        """
        Scan receipt and match products, but DON'T add to inventory yet.
        Returns matched items for user confirmation.
        
        Returns:
            dict with receipt_id, matched_items (ready for confirmation)
        """
        try:
            # Step 1: Upload image to Supabase Storage
            print(f"[*] Uploading receipt image for user {user_id}...")
            storage_result = self.storage_service.upload_receipt_image(
                user_id=user_id,
                file_data=image_data,
                file_name=file_name,
                content_type=content_type
            )
            image_url = storage_result["public_url"]
            image_path = storage_result["path"]
            print(f"[+] Image uploaded: {image_url}")
            
            # Step 2: Scan receipt with AI
            print(f"[*] Scanning receipt with AI...")
            scan_result = self.scanner_service.scan_receipt_from_url(image_url)
            print(f"[+] Found {len(scan_result.items)} items in receipt")
            
            # Step 3: Match products and create missing ones
            print(f"[*] Matching products...")
            matched_items = self._match_or_create_products(scan_result)
            print(f"[+] Processed {len(matched_items)} items")
            
            # Step 4: Create receipt in database (without items yet)
            print(f"[*] Saving receipt to database...")
            receipt_create = ReceiptCreate(
                store_name=scan_result.store_name,
                purchased_at=datetime.fromisoformat(scan_result.purchase_date) if scan_result.purchase_date else datetime.utcnow(),
                total_amount=scan_result.total_amount,
                raw_text=scan_result.raw_text,
                items=[]  # Will add items later after user confirmation
            )
            
            receipt = self.receipt_service.create_receipt(user_id, receipt_create)
            receipt_id = receipt["receipt_id"]
            print(f"[+] Receipt saved with ID: {receipt_id}")
            
            # Return data for user confirmation
            return {
                "success": True,
                "receipt_id": receipt_id,
                "receipt": receipt,
                "matched_items": matched_items,
                "image_url": image_url,
                "stats": {
                    "total_items": len(matched_items),
                    "new_products": sum(1 for item in matched_items if item["is_new_product"]),
                    "matched_products": sum(1 for item in matched_items if not item["is_new_product"])
                }
            }
            
        except Exception as e:
            print(f"[-] Error processing receipt: {e}")
            # Try to clean up uploaded image on failure
            try:
                if 'image_path' in locals():
                    self.storage_service.delete_receipt_image(image_path)
            except:
                pass
            raise Exception(f"Failed to process receipt: {str(e)}")
    
    def confirm_and_add_to_inventory(
        self,
        user_id: UUID,
        receipt_id: str,
        confirmed_items: List[dict]
    ) -> dict:
        """
        After user confirmation, add items to inventory as FULL and create logs
        
        confirmed_items format:
        [
            {
                "product_id": "uuid",
                "quantity": 2.0,
                "unit_price": 10.5,
                "detected_name": "Milk"
            }
        ]
        """
        try:
            added_items = []
            inventory_updates = []
            
            for item in confirmed_items:
                product_id = item["product_id"]
                quantity = item.get("quantity", 1.0)
                
                # Create receipt item
                receipt_item_data = {
                    "product_id": product_id,
                    "detected_name": item.get("detected_name", ""),
                    "quantity": quantity,
                    "unit_price": item.get("unit_price"),
                    "total_price": item.get("total_price"),
                    "confidence": item.get("confidence", 0.9)
                }
                receipt_item = self.receipt_service.create_receipt_item(receipt_id, receipt_item_data)
                added_items.append(receipt_item)
                
                # Check if product exists in user's inventory
                existing_inventory = self.supabase.table("inventory").select("*").eq(
                    "user_id", str(user_id)
                ).eq("product_id", product_id).execute()
                
                if existing_inventory.data and len(existing_inventory.data) > 0:
                    # Update existing inventory - ADD to existing quantity
                    existing = existing_inventory.data[0]
                    current_qty = existing.get("estimated_qty", 0) or 0
                    new_qty = current_qty + quantity
                    
                    update_result = self.supabase.table("inventory").update({
                        "state": "FULL",
                        "last_source": "RECEIPT",
                        "estimated_qty": new_qty,
                        "last_updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("user_id", str(user_id)).eq("product_id", product_id).execute()
                    
                    print(f"[+] Updated inventory: {existing.get('displayed_name')} - {current_qty} + {quantity} = {new_qty}")
                    
                    inventory_updates.append({
                        "product_id": product_id,
                        "action": "updated",
                        "state": "FULL",
                        "old_qty": current_qty,
                        "new_qty": new_qty
                    })
                else:
                    # Create new inventory item as FULL
                    product = self.product_service.get_product(product_id)
                    insert_result = self.supabase.table("inventory").insert({
                        "user_id": str(user_id),
                        "product_id": product_id,
                        "state": "FULL",
                        "estimated_qty": quantity,
                        "qty_unit": product.get("default_unit", "units"),
                        "confidence": 1.0,
                        "last_source": "RECEIPT",
                        "displayed_name": product.get("product_name")
                    }).execute()
                    
                    inventory_updates.append({
                        "product_id": product_id,
                        "action": "created",
                        "state": "FULL"
                    })
                
                # Create inventory log entry with receipt_item_id linkage
                log_entry = {
                    "user_id": str(user_id),
                    "product_id": product_id,
                    "action": "PURCHASE",
                    "delta_state": "FULL",
                    "action_confidence": 1.0,
                    "source": "RECEIPT",
                    "receipt_item_id": receipt_item.get("receipt_item_id"),
                    "note": f"Purchased {quantity} units from receipt",
                    "delta_qty": quantity  # Add quantity to log
                }
                log_result = self.supabase.table("inventory_log").insert(log_entry).execute()
                
                # Update predictor with the purchase data
                if log_result.data and len(log_result.data) > 0:
                    log_id = log_result.data[0].get("log_id")
                    try:
                        from app.services.predictor_service import PredictorService
                        predictor_service = PredictorService(self.supabase)
                        
                        # Process the log to create predictor state and forecast
                        predictor_service.process_inventory_log(str(log_id))
                        
                        print(f"[+] Predictor updated for product {product_id} with quantity {quantity}")
                    except Exception as pred_err:
                        print(f"[!] Warning: Could not update predictor: {pred_err}")
            
            print(f"[+] Added {len(added_items)} items to inventory with logs and predictor updates")
            
            return {
                "success": True,
                "receipt_items_created": len(added_items),
                "inventory_updates": inventory_updates,
                "total_quantity": sum(item.get("quantity", 1.0) for item in confirmed_items)
            }
            
        except Exception as e:
            print(f"❌ Error adding items to inventory: {e}")
            raise Exception(f"Failed to add items to inventory: {str(e)}")
    
    def _match_or_create_products(
        self,
        scan_result: ReceiptScanResult
    ) -> List[dict]:
        """
        Match scanned items to existing products or create new ones
        
        Returns:
            List of matched items with product_id and metadata
        """
        matched_items = []
        
        # Get all existing products
        existing_products = self.product_service.get_all_products()
        print(f"[*] Found {len(existing_products)} existing products in database")
        
        for scanned_item in scan_result.items:
            # Try to find matching product
            best_match, score = self._find_best_product_match(
                scanned_item.name,
                existing_products
            )
            
            if best_match and score >= 0.75:  # 75% similarity threshold
                # Use existing product
                # Extract category name (handles nested product_categories)
                category_name = None
                if "product_categories" in best_match and isinstance(best_match["product_categories"], dict):
                    category_name = best_match["product_categories"].get("category_name")
                elif "category_name" in best_match:
                    category_name = best_match["category_name"]
                
                matched_items.append({
                    "product_id": best_match["product_id"],
                    "product_name": best_match["product_name"],
                    "detected_name": scanned_item.name,
                    "quantity": scanned_item.quantity,
                    "unit_price": scanned_item.unit_price,
                    "total_price": scanned_item.total_price,
                    "category": category_name,
                    "confidence": scanned_item.confidence,
                    "match_score": score,
                    "is_new_product": False
                })
                print(f"  [+] Matched '{scanned_item.name}' -> '{best_match['product_name']}' (score: {score:.2f})")
            else:
                # Create new product
                print(f"  + Creating new product: '{scanned_item.name}'")
                new_product = self._create_product_from_scan(scanned_item)
                matched_items.append({
                    "product_id": new_product["product_id"],
                    "product_name": new_product["product_name"],
                    "detected_name": scanned_item.name,
                    "quantity": scanned_item.quantity,
                    "unit_price": scanned_item.unit_price,
                    "total_price": scanned_item.total_price,
                    "category": scanned_item.category,
                    "confidence": scanned_item.confidence,
                    "match_score": 0.0,
                    "is_new_product": True
                })
                # Add to existing products for next iterations
                existing_products.append(new_product)
        
        return matched_items
    
    def _find_best_product_match(
        self,
        scanned_name: str,
        existing_products: List[dict]
    ) -> Tuple[Optional[dict], float]:
        """
        Find best matching product using fuzzy string matching
        
        Returns:
            (best_match_product, similarity_score)
        """
        best_match = None
        best_score = 0.0
        
        scanned_name_lower = scanned_name.lower().strip()
        
        for product in existing_products:
            # Handle both direct product_name and nested structures
            if isinstance(product, dict):
                product_name = product.get("product_name", "").lower().strip()
            else:
                product_name = getattr(product, "product_name", "").lower().strip()
            
            if not product_name:
                continue
            
            # Calculate similarity score
            score = SequenceMatcher(None, scanned_name_lower, product_name).ratio()
            
            # Boost score for exact substring matches
            if scanned_name_lower in product_name or product_name in scanned_name_lower:
                score = max(score, 0.85)
            
            if score > best_score:
                best_score = score
                best_match = product
        
        return best_match, best_score
    
    def _create_product_from_scan(self, scanned_item) -> dict:
        """
        Create a new product from scanned receipt item
        """
        # Find or create category
        category_id = None
        if scanned_item.category:
            category_id = self._get_or_create_category(scanned_item.category)
        
        # Create product using schema
        product_create = ProductCreate(
            product_name=scanned_item.name,
            category_id=category_id,
            default_unit="units",
            barcode=None
        )
        
        return self.product_service.create_product(product_create)
    
    def _get_or_create_category(self, category_name: str) -> Optional[str]:
        """
        Get existing category or create new one
        """
        try:
            # Try to find existing category (case-insensitive)
            categories = self.product_service.get_all_categories()
            for cat in categories:
                if cat["category_name"].lower() == category_name.lower():
                    return cat["category_id"]
            
            # Create new category using schema
            category_create = ProductCategoryCreate(category_name=category_name)
            new_category = self.product_service.create_category(category_create)
            return new_category["category_id"]
        except Exception as e:
            print(f"[!] Error creating category: {e}")
            return None
    
    def _calculate_average_confidence(self, scan_result: ReceiptScanResult) -> float:
        """Calculate average confidence of all scanned items"""
        if not scan_result.items:
            return 0.0
        total_confidence = sum(item.confidence for item in scan_result.items)
        return total_confidence / len(scan_result.items)
