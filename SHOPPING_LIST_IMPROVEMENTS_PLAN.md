# Shopping List Improvements and Model Integration Plan

## Overview
This plan addresses issues with Shopping List functionality and integrates the predictor model into the Active Shopping List experience, including quantity recommendations, sufficiency analysis, and model learning from purchase feedback.

## Current Issues Identified

### 1. Shopping List Issues
- Items may not be properly sorted when added
- No connection to model predictions when adding items
- Missing recommended quantity calculation based on model

### 2. Active Shopping List Missing Features
- No model prediction display (days left, state)
- No quantity sufficiency analysis
- No feedback mechanism when buying less/more than recommended

## Implementation Plan

### Phase 1: Fix Shopping List Backend & Frontend

#### 1.1 Backend: Add Sorting to Shopping List Items
**File**: `app/services/shopping_list_service.py`
- Modify `get_shopping_list_items()` to order by `priority DESC, created_at ASC`
- Ensure consistent ordering when items are added

#### 1.2 Backend: Calculate Recommended Quantity When Adding Items
**File**: `app/services/shopping_list_service.py`
- Modify `create_shopping_list_item()` to:
  - If `product_id` exists, calculate recommended quantity based on:
    - Current inventory state (from `inventory` table)
    - Days until next shopping (from user preferences/habits)
    - Model prediction (days_left from inventory)
  - Formula: `recommended_qty = max(1, ceil(days_until_shopping / cycle_mean_days))`
  - If inventory state is LOW/EMPTY, increase recommendation
  - Store in `recommended_qty` field

**New Method**: Add `_calculate_recommended_qty()` helper:
```python
def _calculate_recommended_qty(self, user_id: UUID, product_id: UUID, shopping_frequency_days: int = 7) -> float:
    # Get inventory item
    # Get predictor state (cycle_mean_days)
    # Calculate: days_until_shopping / cycle_mean_days
    # Adjust based on current state
```

#### 1.3 Frontend: Fix Item Addition and Display
**File**: `FRONT/src/app/dashboard/shopping/page.tsx`
- Ensure items are displayed in sorted order (by priority, then created_at)
- Show recommended quantity when adding items
- Display model prediction info if available

### Phase 2: Add Model Prediction to Active Shopping List

#### 2.1 Backend: Create Prediction Endpoint for Shopping Items
**File**: `app/api/shopping_lists.py`
- Add new endpoint: `GET /shopping-lists/{shopping_list_id}/items/{item_id}/prediction`
- Returns:
  - `predicted_days_left`: Days the current inventory will last
  - `predicted_state`: FULL/MEDIUM/LOW/EMPTY
  - `recommended_qty`: Recommended quantity to buy
  - `will_sufficient`: Boolean - will recommended_qty last until next shopping?
  - `confidence`: Model confidence

**Implementation**:
- Get inventory item for product
- Get predictor state
- Calculate prediction using model
- Compare `recommended_qty * cycle_mean_days` vs `shopping_frequency_days`

#### 2.2 Backend: Enhance Shopping List Items Response
**File**: `app/services/shopping_list_service.py`
- Modify `get_shopping_list_items()` to include prediction data:
  - Join with `inventory` table to get current state
  - Calculate prediction for each item with `product_id`
  - Add fields: `predicted_days_left`, `predicted_state`, `will_sufficient`

#### 2.3 Frontend: Display Model Predictions
**File**: `FRONT/src/app/dashboard/shopping-active/page.tsx`
- Add prediction display for each item:
  - Show "Predicted to last: X days"
  - Show state badge (FULL/MEDIUM/LOW/EMPTY)
  - Show "Will this quantity last until next shopping?" with Yes/No indicator
  - Allow user to adjust if prediction seems wrong

**UI Components**:
- Add prediction card below each item
- Show color-coded state indicator
- Add "Sufficient?" toggle/checkbox
- Show recommended quantity prominently

### Phase 3: Quantity Sufficiency Marking

#### 3.1 Backend: Add Sufficiency Feedback Field
**Database**: Add to `shopping_list_items` table:
- `sufficiency_marked`: Boolean (nullable) - user marked if quantity is sufficient
- `actual_qty_purchased`: Numeric (nullable) - actual quantity bought
- `qty_feedback`: Text (nullable) - "LESS", "MORE", "EXACT", "NOT_ENOUGH"

**Migration**: Create `migrations/add_shopping_item_feedback.sql`

#### 3.2 Backend: Update Shopping List Item Schema
**File**: `app/schemas/shopping_list.py`
- Add to `ShoppingListItemUpdate`:
  - `sufficiency_marked: Optional[bool]`
  - `actual_qty_purchased: Optional[float]`
  - `qty_feedback: Optional[str]`

#### 3.3 Frontend: Add Sufficiency Marking UI
**File**: `FRONT/src/app/dashboard/shopping-active/page.tsx`
- Add UI for marking sufficiency:
  - Checkbox: "This quantity will last until next shopping"
  - If unchecked, show options: "Not enough", "Too much", "Just right"
  - Input field for actual quantity purchased (if different from recommended)
- Save feedback when item is marked as BOUGHT

### Phase 4: Model Learning from Purchase Feedback

#### 4.1 Backend: Process Feedback in Complete Shopping
**File**: `app/services/shopping_list_service.py`
- Modify `complete_shopping_list()` to:
  - For each BOUGHT item with `qty_feedback`:
    - Create inventory_log entry with feedback
    - If `qty_feedback == "LESS"`: Create feedback event indicating "bought less than needed"
    - If `qty_feedback == "MORE"`: Create feedback event indicating "bought more than needed"
    - If `qty_feedback == "NOT_ENOUGH"`: Create feedback event indicating "not enough"
    - If `actual_qty_purchased` differs from `recommended_qty`, adjust feedback accordingly

**Integration with Predictor**:
- Use `apply_feedback()` from `ema_cycle_predictor.py`
- Feedback events should update `cycle_mean_days` based on user's actual consumption patterns

#### 4.2 Backend: Create Feedback Event Mapping
**File**: `app/services/shopping_list_service.py`
- Add method to map shopping feedback to predictor feedback events:
  - "LESS" → FeedbackEvent with `more_less` = "LESS"
  - "MORE" → FeedbackEvent with `more_less` = "MORE"
  - "NOT_ENOUGH" → FeedbackEvent with `more_less` = "LESS" (stronger signal)

#### 4.3 Frontend: Collect Feedback on Complete
**File**: `FRONT/src/app/dashboard/shopping-active/page.tsx`
- Before completing shopping, show summary:
  - List items with quantity feedback
  - Allow user to confirm/adjust feedback
  - Send feedback to backend when completing

## Data Flow

```
1. User adds item to Shopping List
   → Backend calculates recommended_qty based on model
   → Item added with recommended_qty

2. User views Active Shopping List
   → Backend fetches items with predictions
   → Frontend displays: predicted_days_left, state, sufficiency analysis

3. User marks item as BOUGHT
   → User can mark sufficiency (will last until next shopping?)
   → User can input actual_qty_purchased
   → Feedback saved to shopping_list_items

4. User completes shopping
   → Backend processes all BOUGHT items
   → Creates inventory_log entries
   → Creates feedback events for model learning
   → Model updates cycle_mean_days based on feedback
```

## Files to Modify

### Backend
1. `app/services/shopping_list_service.py` - Add prediction calculation, feedback processing
2. `app/api/shopping_lists.py` - Add prediction endpoint
3. `app/schemas/shopping_list.py` - Add feedback fields
4. `migrations/add_shopping_item_feedback.sql` - Database migration

### Frontend
1. `FRONT/src/app/dashboard/shopping/page.tsx` - Fix sorting, show recommendations
2. `FRONT/src/app/dashboard/shopping-active/page.tsx` - Add predictions, sufficiency marking

## Testing Considerations

1. Test recommended quantity calculation with different inventory states
2. Test prediction display for items with/without product_id
3. Test feedback collection and model learning
4. Test edge cases: no inventory, no predictor state, missing data

## Notes

- Recommended quantity formula may need tuning based on user feedback
- Sufficiency analysis depends on accurate shopping frequency from user preferences
- Model learning from feedback should be gradual (not immediate drastic changes)

