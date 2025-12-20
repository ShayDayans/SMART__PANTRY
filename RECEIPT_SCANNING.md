# 🧾 Receipt Scanning System

## Overview
The Smart Pantry receipt scanning system uses AI-powered OCR (OpenAI Vision API) to automatically extract items from receipt images, match them with existing products, create new products when needed, and add them to the user's inventory.

## Features

### 1. **AI Receipt Scanning**
- Upload receipt images (JPEG, PNG, etc.)
- Automatic text extraction using OpenAI GPT-4 Vision
- Extracts: product names, quantities, prices, categories
- Translates Hebrew product names to English

### 2. **Smart Product Matching**
- Fuzzy string matching to find existing products (75% similarity threshold)
- Automatic product creation for unmatched items
- Category inference from product names
- Confidence scoring for each match

### 3. **User Confirmation Flow**
- Review all scanned items before adding to inventory
- Select/deselect items
- Adjust quantities
- See match confidence scores
- Identify new products created

### 4. **Inventory Integration**
- Adds confirmed items as FULL state
- Creates inventory log entries with action=PURCHASE
- Triggers predictor model learning
- Updates existing inventory or creates new entries

## Architecture

### Backend Services

#### 1. `StorageService` (`app/services/storage_service.py`)
- Handles Supabase Storage operations
- Uploads receipt images to `PHOTOS` bucket
- Organizes files: `receipts/{user_id}/{timestamp}_{filename}`
- Generates public URLs for images

#### 2. `ReceiptScannerService` (`app/services/receipt_scanner_service.py`)
- OpenAI Vision API integration
- Extracts structured data from receipt images
- Returns `ReceiptScanResult` with items, store info, total

#### 3. `ReceiptProcessingService` (`app/services/receipt_processing_service.py`)
- Main orchestration service
- Coordinates: upload → scan → match → confirm → inventory
- Product matching with fuzzy logic
- Auto-creates missing products and categories

### API Endpoints

#### `POST /api/v1/receipts/scan`
Upload and scan receipt image.

**Request:**
- `file`: Image file (multipart/form-data)
- `user_id`: User UUID (form field)

**Response:**
```json
{
  "success": true,
  "receipt_id": "uuid",
  "matched_items": [
    {
      "product_id": "uuid",
      "product_name": "Milk",
      "detected_name": "חלב",
      "quantity": 2.0,
      "unit_price": 5.50,
      "total_price": 11.00,
      "category": "Dairy",
      "confidence": 0.95,
      "match_score": 0.85,
      "is_new_product": false
    }
  ],
  "image_url": "https://...",
  "stats": {
    "total_items": 10,
    "matched_products": 8,
    "new_products": 2
  }
}
```

#### `POST /api/v1/receipts/{receipt_id}/confirm`
Confirm and add items to inventory.

**Request:**
```json
{
  "user_id": "uuid",
  "confirmed_items": [
    {
      "product_id": "uuid",
      "quantity": 2.0,
      "unit_price": 5.50,
      "total_price": 11.00,
      "detected_name": "Milk",
      "confidence": 0.95
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "receipt_items_created": 10,
  "inventory_updates": [
    {
      "product_id": "uuid",
      "action": "created",
      "state": "FULL"
    }
  ]
}
```

### Frontend

#### `src/app/dashboard/return-shopping/page.tsx`
Complete receipt scanning UI with:
- File upload interface
- AI scanning progress indicator
- Item review table with:
  - Checkbox selection
  - Quantity adjustment (+/-)
  - Confidence badges
  - New product indicators
- Confirmation button
- Success/error feedback

## Setup

### 1. Environment Variables
Add to `.env`:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 2. Install Dependencies
```bash
pip install openai==1.35.0 python-multipart==0.0.9
```

### 3. Supabase Storage
Ensure `PHOTOS` bucket exists in Supabase Storage with public access.

## Usage Flow

1. **User uploads receipt image** → Frontend `/return-shopping` page
2. **Image uploaded to Supabase Storage** → `receipts/{user_id}/...`
3. **OpenAI scans receipt** → Extracts items with GPT-4 Vision
4. **Product matching** → Fuzzy match against existing products
5. **New products created** → For unmatched items
6. **User reviews items** → Select/deselect, adjust quantities
7. **User confirms** → Clicks "Add to Pantry"
8. **Inventory updated** → Items added as FULL state
9. **Logs created** → `inventory_log` entries with action=PURCHASE
10. **Predictor updated** → Model learns from new data

## Product Matching Logic

### Similarity Threshold: 75%
Uses `difflib.SequenceMatcher` for fuzzy matching:
- Exact substring matches → 85% boost
- Case-insensitive comparison
- Best match above threshold → use existing product
- No match → create new product

### Example:
```
Scanned: "Whole Milk 3%"
Existing: "Milk - Whole"
Similarity: 82% → Match found ✓

Scanned: "חלב"
Translated: "Milk"
Existing: "Milk"
Similarity: 100% → Match found ✓

Scanned: "Exotic Tropical Juice"
No matches found → Create new product ✓
```

## Database Impact

### Tables Updated:
1. **`receipts`** - Receipt header info
2. **`receipt_items`** - Individual receipt line items
3. **`products`** - New products created (if needed)
4. **`product_categories`** - New categories (if needed)
5. **`inventory`** - User's pantry updated to FULL
6. **`inventory_log`** - Purchase events logged

## Error Handling

- Invalid image format → 400 Bad Request
- OpenAI API failure → 500 Internal Server Error
- Storage upload failure → Rollback, delete image
- Database errors → Transaction rollback

## Future Enhancements

- [ ] Batch receipt processing
- [ ] Receipt history view
- [ ] Duplicate receipt detection
- [ ] Manual item editing in review screen
- [ ] Category suggestions with ML
- [ ] Multi-language support
- [ ] Price tracking and comparison
- [ ] Store recognition and preferences
- [ ] Barcode extraction from images
- [ ] Auto-splitting shared receipts

## Cost Considerations

**OpenAI Vision API:**
- GPT-4o: ~$0.01 per image (high detail)
- Typical receipt: $0.01-0.02 per scan

**Supabase Storage:**
- 1GB free tier
- Typical receipt image: 1-3MB
- ~300-1000 receipts per GB

## Troubleshooting

### Receipt not scanning?
- Ensure image is clear and well-lit
- Check `OPENAI_API_KEY` is set
- Verify OpenAI account has credits

### Products not matching?
- Adjust similarity threshold (currently 75%)
- Check product names in database
- Review fuzzy matching logic

### Items not added to inventory?
- Check `/confirm` endpoint logs
- Verify user permissions
- Check database constraints

---

**Built with:** FastAPI, OpenAI Vision API, Supabase, React/Next.js

