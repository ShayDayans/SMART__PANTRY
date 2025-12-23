# How Category Affects the Predictor Model

## Overview
The product category plays a crucial role in initializing and guiding the predictor model's behavior. It provides **prior knowledge** about typical consumption patterns for different product types.

## 1. Category Priors (Initial Values)

### Definition
Each category has **default priors** that define expected consumption patterns:
- **`mean_days`**: Average number of days until a product runs out
- **`mad_days`**: Mean Absolute Deviation (variability/uncertainty)

### Default Priors by Category

Located in `app/services/predictor_service.py`:

```python
{
    "Dairy & Eggs": {"mean_days": 5.0, "mad_days": 2.0},      # Fast consumption
    "Bread & Bakery": {"mean_days": 4.0, "mad_days": 1.5},   # Very fast
    "Meat & Poultry": {"mean_days": 4.0, "mad_days": 2.0},   # Fast
    "Fish & Seafood": {"mean_days": 3.0, "mad_days": 1.5},   # Very fast
    "Fruits": {"mean_days": 6.0, "mad_days": 2.5},           # Medium
    "Vegetables": {"mean_days": 5.0, "mad_days": 2.0},      # Medium
    "Grains & Pasta": {"mean_days": 35.0, "mad_days": 10.0}, # Long shelf life
    "Canned & Jarred": {"mean_days": 75.0, "mad_days": 15.0}, # Very long
    "Condiments & Sauces": {"mean_days": 45.0, "mad_days": 15.0}, # Long
    "Snacks": {"mean_days": 10.0, "mad_days": 5.0},         # Medium
    "Beverages": {"mean_days": 7.0, "mad_days": 3.0},       # Medium
    "Frozen Foods": {"mean_days": 45.0, "mad_days": 15.0},   # Long
    "Spices & Seasonings": {"mean_days": 75.0, "mad_days": 20.0}, # Very long
}
```

### Default for Unknown Categories
If a category is not found or product has no category:
- **`mean_days`**: 7.0 days
- **`mad_days`**: 2.0 days

## 2. Model Initialization (Cold Start)

### Process
When a **new product** is added to inventory (no existing predictor state):

1. **Get category_id** from `products.category_id`
2. **Look up category prior** in `cfg.category_priors` (mapped by category_id)
3. **Initialize state** using `init_state_from_category()`:

```python
# From ema_cycle_predictor.py
def init_state_from_category(category_id, cfg, now):
    prior = cfg.category_priors.get(str(category_id))
    if prior is None:
        prior = CategoryPrior(mean_days=7.0, mad_days=2.0)  # Default
    
    return CycleEmaState(
        cycle_mean_days=prior.mean_days,  # Initial cycle length
        cycle_mad_days=prior.mad_days,    # Initial variability
        category_id=str(category_id),      # Store category for reference
        # ... other fields initialized to defaults
    )
```

### Impact
- **Fast-consumption categories** (Dairy, Bread, Meat): Start with low `cycle_mean_days` (3-5 days)
- **Long-shelf-life categories** (Canned, Spices): Start with high `cycle_mean_days` (45-75 days)
- **Medium categories** (Fruits, Vegetables): Start with moderate `cycle_mean_days` (5-7 days)

## 3. State Storage

### Category ID in State
The `category_id` is stored in the predictor state (`CycleEmaState`):
- Allows tracking which category the product belongs to
- Can be used for category-specific learning or analysis
- Updated if product category changes: `if st.category_id is None and category_id is not None: st.category_id = str(category_id)`

## 4. Learning Process

### How Model Learns from User Behavior

1. **Initial State**: Starts with category priors
2. **User Actions**: Each purchase, consumption, or feedback event updates the state
3. **EMA Updates**: Uses Exponential Moving Average to adjust `cycle_mean_days` and `cycle_mad_days`
4. **Personalization**: Over time, the model learns the user's specific consumption patterns

### Example Learning Flow

```
Initial: category="Dairy & Eggs" → cycle_mean_days=5.0
  ↓
User purchases milk → apply_purchase() → cycle_mean_days adjusts
  ↓
User marks as empty after 4 days → apply_feedback() → cycle_mean_days decreases
  ↓
After several cycles → cycle_mean_days=3.5 (personalized to user)
```

## 5. Category Usage in Predictions

### Current Implementation
- **Initialization only**: Category priors are used **only at cold start**
- **Not used during updates**: Once the model has learned from user data, category priors are not directly used
- **Habits multiplier**: Category can affect habits multiplier (temporary consumption changes)

### Prediction Formula
```python
days_left = (cycle_mean_days - elapsed_days) / habit_multiplier
```

Where:
- `cycle_mean_days`: Learned from user behavior (started from category prior)
- `elapsed_days`: Time since cycle started
- `habit_multiplier`: Can be category-specific (from habits table)

## 6. Category Changes

### What Happens When Category is Updated?

**Current Behavior:**
- If product category changes, the `category_id` in state is updated
- **BUT**: The learned `cycle_mean_days` and `cycle_mad_days` are **NOT reset**
- The model continues with its learned values

**Potential Improvement:**
- Could reset state when category changes significantly
- Could blend old learned values with new category priors

## 7. Key Files

- **`app/services/predictor_service.py`**: Category priors definition, initialization
- **`ema_cycle_predictor.py`**: `init_state_from_category()` function
- **`app/services/predictor_service.py`**: `_load_or_init_state()` - uses category for initialization
- **`app/services/predictor_service.py`**: `process_inventory_log()` - gets category_id from products

## Summary

**Category Impact:**
1. ✅ **Initialization**: Provides starting point for new products
2. ✅ **Cold Start**: Helps model make reasonable predictions before learning user behavior
3. ✅ **Storage**: Category ID stored in state for reference
4. ⚠️ **Learning**: Model learns from user behavior, category priors become less relevant over time
5. ⚠️ **Category Changes**: Changing category doesn't reset learned values (potential improvement area)

**Key Insight**: Category is most important for **new products** without history. Once the model learns user patterns, category priors have less direct impact, but the initial values influence how quickly the model converges to user-specific patterns.

