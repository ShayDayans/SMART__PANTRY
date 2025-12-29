# 📝 הסבר מפורט על כל הפידבקים מהמשתמש

קובץ זה מסביר את כל המקומות באפליקציה שבהם המשתמש נותן פידבק, איך המודל מתעדכן, ואיך זה משפיע על הפרמטרים.

---

## 🎯 סיכום מהיר

| מיקום | סוג פידבק | מתעדכן `days_left`? | מתעדכן `cycle_mean_days`? | מתי `cycle_mean_days` מתעדכן? |
|-------|-----------|---------------------|---------------------------|-------------------------------|
| **Purchase** | Shopping List Complete | ✅ מיד (cycle_mean_days) | ❌ לא | רק ב-weekly update |
| **Pantry Page** | MORE/LESS | ✅ מיד | ❌ לא | רק ב-weekly update (אם עבר שבוע) |
| **Shopping List** | Will Last More/Less | ✅ מיד | ❌ לא | רק ב-weekly update (אם עבר שבוע) |
| **Shopping List** | Adjust Days (↑↓) | ✅ מיד | ❌ לא | רק ב-weekly update (אם עבר שבוע) |
| **Pantry Actions** | Thrown Away | ✅ מיד | ✅ מיד (תלוי בסיבה) | מיד (אם סיבה = "ran out") |
| **Pantry Actions** | Repurchased | ✅ מיד | ❌ לא | רק ב-weekly update |
| **Pantry Actions** | Ran Out | ✅ מיד | ✅ מיד | מיד (cumulative average) |
| **Recipe Cooking** | Step Complete | ✅ מיד | ❌ לא | רק ב-weekly update |

---

## 0️⃣ Purchase (קנייה) - Shopping List Complete

### 📍 מיקום
**קובץ:** `app/services/shopping_list_service.py`  
**Endpoint:** `POST /api/v1/shopping-lists/{shopping_list_id}/complete`  
**Frontend:** `FRONT/src/app/dashboard/shopping-active/page.tsx`

### 🔄 איך זה עובד
המשתמש מסיים את רשימת הקניות ולוחץ על "Complete Shopping List".

### ✅ האם המודל מתעדכן?
**כן** - `days_left` מתעדכן מיד ל-`cycle_mean_days`, אבל **לא** `cycle_mean_days` עצמו.

### 📊 איך זה משפיע על `days_left`?

**חשוב:** קנייה מתחילה מחזור חדש, אז ה-`days_left` הקודם לא נשמר!

```python
# אחרי PURCHASE:
cycle_started_at = now  # מחזור חדש התחיל
elapsed = 0  # עוד לא עבר זמן
days_left = cycle_mean_days - elapsed = cycle_mean_days
```

**דוגמה:**
- לפני קנייה: `days_left = 2`, `cycle_mean_days = 7`
- אחרי קנייה: `days_left = 7` (מחזור חדש!), `state = FULL`

**הערה:** ה-2 ימים שהיו לפני הקנייה לא נשמרים - הקנייה מתחילה מחזור חדש.

### 📈 איך זה משפיע על `cycle_mean_days`?
**לא משפיע מיד!** `cycle_mean_days` מתעדכן רק ב-**weekly update** (אם עבר שבוע מאז יצירת המוצר).

**אבל:** אם היה מחזור פעיל לפני הקנייה, הוא מסומן כ-**censored** (לא הושלם):
```python
if state.cycle_started_at is not None:
    state.censored_cycles += 1  # המחזור הקודם לא הושלם
```

### 🔧 מה מתעדכן מיד?
1. ✅ `inventory.estimated_qty` = `cycle_mean_days` (מחזור חדש)
2. ✅ `inventory.state` = `FULL` (אם `ratio = days_left / cycle_mean_days >= 0.70`)
3. ✅ `inventory_log` - נוצר log entry עם `action=PURCHASE`
4. ✅ `product_predictor_state` - מעודכן דרך `process_inventory_log`:
   - `cycle_started_at` = `now` (מחזור חדש התחיל)
   - `last_purchase_at` = `now`
   - `censored_cycles` += 1 (אם היה מחזור פעיל)
   - `last_pred_days_left` = `cycle_mean_days`

### 💡 דוגמה מפורטת

**תרחיש:**
- `cycle_mean_days = 7`
- לפני קנייה: `days_left = 2`, `state = LOW`
- המשתמש קונה את המוצר

**אחרי קנייה:**
- `days_left = 7` (מחזור חדש התחיל!)
- `state = FULL` (ratio = 7/7 = 1.0 >= 0.70)
- `cycle_started_at = now`
- `censored_cycles += 1` (המחזור הקודם לא הושלם)

**הערה חשובה:** ה-2 ימים שהיו לפני הקנייה לא נשמרים - הקנייה מתחילה מחזור חדש עם `days_left = cycle_mean_days`.

---

## 1️⃣ Pantry Page - MORE/LESS Feedback

### 📍 מיקום
**קובץ:** `app/api/inventory.py`  
**Endpoint:** `POST /api/v1/inventory/{product_id}/feedback`  
**Frontend:** `FRONT/src/app/dashboard/pantry/page.tsx`

### 🔄 איך זה עובד
המשתמש לוחץ על כפתור "More" או "Less" בעמוד ה-Pantry.

### ✅ האם המודל מתעדכן?
**כן** - `days_left` מתעדכן מיד, אבל **לא** `cycle_mean_days`.

### 📊 איך זה משפיע על `days_left`?

#### מקרה 1: מוצר לא EMPTY
```python
if direction == "more":
    multiplier = 1.15  # 15% יותר ימים
    new_days_left = current_days_left * 1.15
else:  # less
    multiplier = 0.85  # 15% פחות ימים
    new_days_left = current_days_left * 0.85
```

**דוגמה:**
- לפני: `days_left = 5`
- אחרי MORE: `days_left = 5 * 1.15 = 5.75`
- אחרי LESS: `days_left = 5 * 0.85 = 4.25`

#### מקרה 2: מוצר EMPTY
```python
if direction == "more":
    # אם EMPTY ולחצת MORE = יש לך את המוצר שוב
    new_days_left = cycle_mean_days * 0.15  # 15% מהממוצע
else:  # less
    new_days_left = 0.0  # נשאר EMPTY
```

**דוגמה:**
- `cycle_mean_days = 7`
- אחרי MORE: `days_left = 7 * 0.15 = 1.05`

### 📈 איך זה משפיע על `cycle_mean_days`?
**לא משפיע מיד!** `cycle_mean_days` מתעדכן רק ב-**weekly update** (אם עבר שבוע מאז יצירת המוצר).

### 🔧 מה מתעדכן מיד?
1. ✅ `inventory.estimated_qty` = `new_days_left`
2. ✅ `inventory.state` = `derive_state(new_days_left, cycle_mean_days)`
3. ✅ `product_predictor_state.params.last_pred_days_left` = `new_days_left`
4. ✅ `product_predictor_state.last_update_at` = `now`
5. ✅ `product_predictor_state.confidence` = `compute_confidence(...)`
6. ✅ `inventory_log` - נוצר log entry עם `action=ADJUST`

---

## 2️⃣ Shopping List - Will Last More/Less

### 📍 מיקום
**קובץ:** `app/api/predictor.py`  
**Endpoint:** `POST /api/v1/predictor/learn-from-shopping-feedback`  
**Frontend:** `FRONT/src/app/dashboard/shopping-active/page.tsx`

### 🔄 איך זה עובד
המשתמש לוחץ על "Will Last More" או "Will Last Less" ברשימת הקניות הפעילה.

### ✅ האם המודל מתעדכן?
**כן** - `days_left` מתעדכן מיד, אבל **לא** `cycle_mean_days`.

### 📊 איך זה משפיע על `days_left`?

#### מקרה 1: מוצר לא EMPTY
```python
if feedback_kind == "MORE":
    multiplier = 1.15  # 15% יותר ימים
    new_days_left = current_days_left * 1.15
else:  # LESS
    multiplier = 0.85  # 15% פחות ימים
    new_days_left = current_days_left * 0.85
```

**דוגמה:**
- לפני: `days_left = 6`
- אחרי MORE: `days_left = 6 * 1.15 = 6.9`
- אחרי LESS: `days_left = 6 * 0.85 = 5.1`

#### מקרה 2: מוצר EMPTY
```python
if feedback_kind == "MORE":
    new_days_left = cycle_mean_days * 0.15  # 15% מהממוצע
else:  # LESS
    new_days_left = 0.0  # נשאר EMPTY
```

### 📈 איך זה משפיע על `cycle_mean_days`?
**לא משפיע מיד!** `cycle_mean_days` מתעדכן רק ב-**weekly update** (אם עבר שבוע מאז יצירת המוצר).

### 🔧 מה מתעדכן מיד?
1. ✅ `inventory.estimated_qty` = `new_days_left`
2. ✅ `inventory.state` = `derive_state(new_days_left, cycle_mean_days)`
3. ✅ `product_predictor_state.params.last_pred_days_left` = `new_days_left`
4. ✅ `product_predictor_state.last_update_at` = `now`
5. ✅ `product_predictor_state.confidence` = `compute_confidence(...)`
6. ✅ `shopping_feedback_log` - נוצר log entry עם הפידבק
7. ✅ `inventory_log` - נוצר log entry עם `action=ADJUST`

---

## 3️⃣ Shopping List - Adjust Days (↑↓)

### 📍 מיקום
**קובץ:** `app/api/predictor.py`  
**Endpoint:** `POST /api/v1/predictor/learn-from-shopping-feedback`  
**Frontend:** `FRONT/src/app/dashboard/shopping-active/page.tsx`

### 🔄 איך זה עובד
המשתמש לוחץ על חץ למעלה (↑) או למטה (↓) כדי להתאים את מספר הימים.

### ✅ האם המודל מתעדכן?
**כן** - `days_left` מתעדכן מיד, אבל **לא** `cycle_mean_days`.

### 📊 איך זה משפיע על `days_left`?
זה בעצם אותו דבר כמו "Will Last More/Less":
- ↑ = MORE → `new_days_left = current_days_left * 1.15`
- ↓ = LESS → `new_days_left = current_days_left * 0.85`

### 📈 איך זה משפיע על `cycle_mean_days`?
**לא משפיע מיד!** `cycle_mean_days` מתעדכן רק ב-**weekly update**.

### 🔧 מה מתעדכן מיד?
אותו דבר כמו "Will Last More/Less" (ראה סעיף 2).

---

## 4️⃣ Pantry Actions - Thrown Away (נזרק)

### 📍 מיקום
**קובץ:** `app/api/inventory.py`  
**Endpoint:** `POST /api/v1/inventory/{product_id}/action`  
**Frontend:** `FRONT/src/app/dashboard/pantry/page.tsx`

### 🔄 איך זה עובד
המשתמש מסמן שהמוצר נזרק (Thrown Away) ובוחר סיבה (לא היה טעים, פג תוקף, אחר).

### ✅ האם המודל מתעדכן?
**כן** - גם `days_left` וגם `cycle_mean_days` (תלוי בסיבה).

### 📊 איך זה משפיע על `days_left`?
```python
days_left = 0.0  # המוצר נזרק = EMPTY
state = EMPTY
```

### 📈 איך זה משפיע על `cycle_mean_days`?
**תלוי בסיבה!**

#### סיבה = "לא היה טעים" או "פג תוקף"
```python
# זה לא אירוע צריכה - לא מעדכן cycle_mean_days
# רק מעדכן:
cycle_started_at = None  # מבטל את המחזור הנוכחי
days_left = 0.0
state = EMPTY
```

#### סיבה = "נגמר" או "empty"
```python
# זה אירוע צריכה חלש - מעדכן cycle_mean_days חלש מאוד
# משתמש ב-20% מ-alpha_strong
observed = days_between(now, cycle_started_at)
alpha_weak = alpha_strong * 0.20
new_mean = (1 - alpha_weak) * old_mean + alpha_weak * observed
```

### 🔧 מה מתעדכן מיד?
1. ✅ `inventory.estimated_qty` = `0.0`
2. ✅ `inventory.state` = `EMPTY`
3. ✅ `inventory_log` - נוצר log entry עם `action=TRASH` ו-`note="WASTED: {reason}"`
4. ✅ `product_predictor_state` - מעודכן דרך `process_inventory_log`

---

## 5️⃣ Pantry Actions - Repurchased (נקנה מחדש)

### 📍 מיקום
**קובץ:** `app/api/inventory.py`  
**Endpoint:** `POST /api/v1/inventory/{product_id}/action`  
**Frontend:** `FRONT/src/app/dashboard/pantry/page.tsx`

### 🔄 איך זה עובד
המשתמש מסמן שהמוצר נקנה מחדש (Repurchased) ובוחר סיבה (נגמר, מוצר היה פגום, אחר).

### ✅ האם המודל מתעדכן?
**כן** - `days_left` מתעדכן מיד, אבל **לא** `cycle_mean_days`.

### 📊 איך זה משפיע על `days_left`?
```python
# יוצר שני log entries:
# 1. REPURCHASE (מבטל את המחזור הקודם)
# 2. PURCHASE (מתחיל מחזור חדש)

# אחרי PURCHASE:
days_left = cycle_mean_days  # מחזור חדש התחיל
state = FULL (אם ratio >= 0.70)
```

**דוגמה:**
- `cycle_mean_days = 7`
- אחרי REPURCHASE: `days_left = 7`, `state = FULL`

### 📈 איך זה משפיע על `cycle_mean_days`?
**לא משפיע מיד!** `cycle_mean_days` מתעדכן רק ב-**weekly update** (אם עבר שבוע מאז יצירת המוצר).

### 🔧 מה מתעדכן מיד?
1. ✅ `inventory.estimated_qty` = `cycle_mean_days`
2. ✅ `inventory.state` = `FULL` (אם ratio >= 0.70)
3. ✅ `inventory_log` - נוצרים שני log entries:
   - `action=REPURCHASE` עם `note="PURCHASE: {reason}"`
   - `action=PURCHASE` עם `note="PURCHASE: {reason}"`
4. ✅ `product_predictor_state` - מעודכן דרך `process_inventory_log`:
   - `cycle_started_at` = `now`
   - `last_purchase_at` = `now`

---

## 6️⃣ Pantry Actions - Ran Out (נגמר)

### 📍 מיקום
**קובץ:** `app/api/inventory.py`  
**Endpoint:** `POST /api/v1/inventory/{product_id}/action`  
**Frontend:** `FRONT/src/app/dashboard/pantry/page.tsx`

### 🔄 איך זה עובד
המשתמש מסמן שהמוצר נגמר (Ran Out) ובוחר סיבה.

### ✅ האם המודל מתעדכן?
**כן** - גם `days_left` וגם `cycle_mean_days` מתעדכנים מיד!

### 📊 איך זה משפיע על `days_left`?
```python
days_left = 0.0  # המוצר נגמר = EMPTY
state = EMPTY
```

### 📈 איך זה משפיע על `cycle_mean_days`?
**מתעדכן מיד עם cumulative average!**

```python
# מחשב את אורך המחזור שנצפה
observed = days_between(now, cycle_started_at)

# מעדכן עם ממוצע מצטבר
n_cycles = state.n_completed_cycles
if n_cycles == 0:
    new_mean = observed
else:
    new_mean = (old_mean * n_cycles + observed) / (n_cycles + 1)

# מעדכן גם MAD
if n_cycles == 0:
    new_mad = abs(observed - old_mean)
else:
    current_mad_sum = state.cycle_mad_days * n_cycles
    new_mad = (current_mad_sum + abs(observed - old_mean)) / (n_cycles + 1)

# מעדכן
state.cycle_mean_days = new_mean
state.cycle_mad_days = new_mad
state.n_completed_cycles += 1
state.cycle_started_at = None  # מחזור הסתיים
```

**דוגמה:**
- מחזור 1: `observed = 7` → `cycle_mean_days = 7`, `n_completed_cycles = 1`
- מחזור 2: `observed = 5` → `cycle_mean_days = (7*1 + 5)/2 = 6`, `n_completed_cycles = 2`
- מחזור 3: `observed = 4` → `cycle_mean_days = (6*2 + 4)/3 = 5.33`, `n_completed_cycles = 3`

### 🔧 מה מתעדכן מיד?
1. ✅ `inventory.estimated_qty` = `0.0`
2. ✅ `inventory.state` = `EMPTY`
3. ✅ `inventory_log` - נוצר log entry עם `action=EMPTY` ו-`note="EMPTY: {reason}"`
4. ✅ `product_predictor_state` - מעודכן דרך `process_inventory_log`:
   - `cycle_mean_days` = ממוצע מצטבר חדש
   - `cycle_mad_days` = MAD חדש
   - `n_completed_cycles` += 1
   - `cycle_started_at` = `None`

---

## 7️⃣ Recipe Cooking - Step Complete

### 📍 מיקום
**קובץ:** `app/api/recipes.py`  
**Endpoint:** `POST /api/v1/recipes/step-complete`  
**Frontend:** `FRONT/src/app/dashboard/recipes/page.tsx`

### 🔄 איך זה עובד
המשתמש מסיים שלב בבישול המתכון ולוחץ על "Step Complete".

### ✅ האם המודל מתעדכן?
**כן** - `days_left` מתעדכן מיד, אבל **לא** `cycle_mean_days`.

### 📊 איך זה משפיע על `days_left`?

#### אם צוין `amount_used`:
```python
new_qty = max(0, current_qty - amount_used)
```

#### אם לא צוין `amount_used`:
```python
# Default: מוריד 10% לכל שלב
new_qty = max(0, current_qty * 0.9)
```

**דוגמה:**
- לפני: `days_left = 5`
- אחרי שלב (10%): `days_left = 5 * 0.9 = 4.5`
- אחרי עוד שלב: `days_left = 4.5 * 0.9 = 4.05`

### 📈 איך זה משפיע על `cycle_mean_days`?
**לא משפיע מיד!** `cycle_mean_days` מתעדכן רק ב-**weekly update** (אם עבר שבוע מאז יצירת המוצר).

### 🔧 מה מתעדכן מיד?
1. ✅ `inventory.estimated_qty` = `new_qty`
2. ✅ `inventory.state` = נגזר מ-`new_qty`:
   - אם `new_qty <= 0` → `EMPTY`
   - אם `new_qty < current_qty * 0.3` → `LOW`
   - אם `new_qty < current_qty * 0.7` → `MEDIUM`
   - אחרת → `FULL`
3. ✅ `inventory_log` - נוצר log entry עם:
   - `action=ADJUST`
   - `source=RECIPE`
   - `note="Recipe step {step_index + 1}: Used {ingredient_name}"`
4. ✅ `product_predictor_state` - מעודכן דרך `process_inventory_log`:
   - `last_pred_days_left` = `new_qty`
   - `last_update_at` = `now`

---

## 📊 טבלת סיכום - השפעה על הפרמטרים

| פידבק | `days_left` | `cycle_mean_days` | `state` | `last_pred_days_left` | `n_completed_cycles` |
|-------|-------------|-------------------|---------|----------------------|----------------------|
| **Purchase** | ✅ מיד (cycle_mean_days) | ❌ רק weekly | ✅ מיד (FULL) | ✅ מיד | ❌ |
| **Pantry MORE/LESS** | ✅ מיד (×1.15/0.85) | ❌ רק weekly | ✅ מיד | ✅ מיד | ❌ |
| **Shopping MORE/LESS** | ✅ מיד (×1.15/0.85) | ❌ רק weekly | ✅ מיד | ✅ מיד | ❌ |
| **Shopping Adjust** | ✅ מיד (×1.15/0.85) | ❌ רק weekly | ✅ מיד | ✅ מיד | ❌ |
| **Thrown Away** | ✅ מיד (0.0) | ✅ מיד (אם סיבה="ran out") | ✅ מיד (EMPTY) | ✅ מיד | ✅ (אם סיבה="ran out") |
| **Repurchased** | ✅ מיד (cycle_mean_days) | ❌ רק weekly | ✅ מיד (FULL) | ✅ מיד | ❌ |
| **Ran Out** | ✅ מיד (0.0) | ✅ מיד (cumulative avg) | ✅ מיד (EMPTY) | ✅ מיד | ✅ (+1) |
| **Recipe Step** | ✅ מיד (-amount או ×0.9) | ❌ רק weekly | ✅ מיד | ✅ מיד | ❌ |

---

## 🔄 מתי `cycle_mean_days` מתעדכן?

### 1. מיד (Immediate Update)
- ✅ **Ran Out** - cumulative average
- ✅ **Thrown Away** (אם סיבה = "ran out") - weak update (20% מ-alpha_strong)

### 2. Weekly Update (אם עבר שבוע)
- ✅ **Pantry MORE/LESS**
- ✅ **Shopping MORE/LESS**
- ✅ **Shopping Adjust**
- ✅ **Repurchased**
- ✅ **Recipe Step**

**לוגיקה:**
```python
# בודק אם עבר שבוע מאז יצירת המוצר
if current_weekday == created_weekday:
    # מעדכן cycle_mean_days לפי המחזורים שהושלמו
    weekly_model_update(user_id, product_id)
```

---

## 🎯 סיכום כללי

### מה מתעדכן מיד?
- ✅ `days_left` - בכל פידבק
- ✅ `state` - בכל פידבק (נגזר מ-`days_left`)
- ✅ `last_pred_days_left` - בכל פידבק
- ✅ `confidence` - בכל פידבק

### מה מתעדכן רק ב-weekly update?
- ❌ `cycle_mean_days` - רק אם עבר שבוע (חוץ מ-Ran Out)
- ❌ `cycle_mad_days` - רק אם עבר שבוע (חוץ מ-Ran Out)

### מה מתעדכן רק ב-Ran Out?
- ✅ `n_completed_cycles` - רק ב-Ran Out (מחזור הושלם)
- ✅ `cycle_mean_days` - cumulative average (רק ב-Ran Out)

---

**הערה חשובה:** כל הפידבקים מתעדכנים ב-`inventory_log` ו-`product_predictor_state`, כך שהמודל יכול ללמוד מהם בעתיד, גם אם `cycle_mean_days` לא מתעדכן מיד.

