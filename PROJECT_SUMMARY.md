# 📋 סיכום מלא של הפרויקט - Smart Pantry

## 🎯 סקירה כללית

מערכת ניהול מזווה חכמה עם מודל חיזוי AI ללמידת דפוסי צריכה אישיים. המערכת כוללת ממשק משתמש מלא, ניהול מלאי, רשימות קניות, יצירת מתכונים, ומערכת למידה מתקדמת.

---

## 🏗️ ארכיטקטורה

### Backend
- **FastAPI** - Framework ל-API
- **Supabase** - Database & Authentication
- **PostgreSQL** - Database
- **OpenAI GPT** - יצירת מתכונים

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **Zustand** - State management

---

## ✨ תכונות עיקריות

### 1. 🔐 מערכת אימות
- התחברות והרשמה עם Supabase Auth
- ניהול סשן משתמש
- הגנה על endpoints עם JWT tokens

### 2. 📦 ניהול מזווה (Pantry)
- **תצוגת מלאי מלאה** עם מצבי מלאי (FULL/MEDIUM/LOW/EMPTY)
- **פילטור לפי קטגוריות** - סינון מוצרים לפי קטגוריה
- **שיוך ידני לקטגוריה** - אפשרות לשנות קטגוריה למוצר
- **פעולות מוצר:**
  - 🗑️ **נזרק (Thrown Away)** - עם סיבות (לא היה טעים, פג תוקף, אחר)
  - 🔄 **נקנה מחדש (Repurchased)** - עם סיבות (נגמר, מוצר פגום, אחר)
  - ⚠️ **נגמר (Ran Out)** - עם סיבות (השתמשתי, אחר)
- **חיזוי AI** - תצוגת ימים שנותרו, confidence, ומצב מוצר
- **עדכון ידני** - אפשרות לעדכן כמות ימים שנותרו
- **UI באנגלית ו-LTR** - כל הממשק באנגלית וכיוון LTR

### 3. 🛒 רשימות קניות (Shopping Lists)
- **יצירת רשימות קניות** - רשימות מרובות למשתמש
- **רשימה פעילה** - רשימה אחת פעילה בכל זמן
- **הוספת מוצרים:**
  - חיפוש בכל המוצרים במערכת (לא רק מהמלאי)
  - **Autocomplete** - הצעות בזמן אמת
  - **יצירת מוצר חדש** - כתיבה חופשית עם חובה לשייך לקטגוריה
  - **הוספה מיידית** - מוצר נוסף מיד לרשימה עם הדגשה ויזואלית
- **חיזוי AI ברשימה:**
  - תצוגת "Enough for X days" לכל מוצר
  - כמות מומלצת לקנייה
  - האם הכמות תספיק עד הקנייה הבאה
- **פידבק בזמן קנייה:**
  - כפתורים "Will Last More" / "Will Last Less"
  - עדכון מיידי של `days_left` (לא `cycle_mean_days`)
  - תיעוד ב-`shopping_feedback_log`
- **סימון מוצרים כנרכשו** - עדכון סטטוס BOUGHT
- **השלמת רשימה** - עדכון אוטומטי של המלאי

### 4. 🍳 יצירת מתכונים (Recipes)
- **מחולל מתכונים מבוסס GPT:**
  - בחירת סגנון ארוחה (dinner, breakfast, lunch)
  - העדפות (מספר מנות, סגנון בישול, זמן בישול, קושי)
  - יצירת מתכון מלא בהתבסס על מוצרים במזווה
  - **בחירה לוגית של מרכיבים** - רק מרכיבים שמתאימים למתכון
  - הצעת מרכיבים נוספים חסרים
- **מתכון מלא כולל:**
  - כותרת ותיאור
  - מספר מנות
  - זמני הכנה ובישול
  - רשימת מרכיבים עם כמויות
  - הוראות שלב אחר שלב
  - טיפים
  - מידע תזונתי
- **מצב בישול מודרך (Guided Cooking):**
  - כפתור "START COOKING"
  - תצוגת הוראות שלב אחר שלב
  - כפתור "Step Complete" לכל שלב
  - עדכון אוטומטי של המלאי אחרי כל שלב
  - עדכון מודל הצריכה עם `source=RECIPE`
  - כפתור "Finish Cooking" לסיום

### 5. 🤖 מודל חיזוי AI (EMA Cycle Predictor)

#### עקרונות יסוד:
- **הפרדה בין `cycle_mean_days` ל-`days_left`:**
  - `cycle_mean_days` = ממוצע מצטבר של כמה ימים המוצר נמשך (מתעדכן רק ב-EMPTY)
  - `days_left` = כמה ימים נשארו למוצר כרגע (מתעדכן בכל פעולה)

#### עדכון `cycle_mean_days`:
- **ממוצע מצטבר (Cumulative Average):**
  ```
  new_mean = (old_mean * n_cycles + new_cycle) / (n_cycles + 1)
  ```
- **מתי מתעדכן:** רק באירוע **EMPTY** (נגמר) - מחזור הושלם
- **לא מתעדכן ב:** MORE/LESS feedback, מתכון, קנייה

#### עדכון `days_left`:
- **קנייה (PURCHASE):** `days_left = cycle_mean_days`
- **נגמר (EMPTY):** `days_left = 0.0`
- **MORE Feedback:** `days_left = current_days_left * 1.15` (15% יותר)
- **LESS Feedback:** `days_left = current_days_left * 0.85` (15% פחות)
- **מתכון (RECIPE):** `days_left = current_days_left - amount_used`
- **EMPTY + MORE:** `days_left = cycle_mean_days * 1.15` (מתחיל מחזור חדש)

#### חישוב `state` (FULL/MEDIUM/LOW/EMPTY):
```
ratio = days_left / cycle_mean_days

if days_left <= 0 or ratio < 0.02:
    state = EMPTY
elif ratio >= 0.70:
    state = FULL
elif ratio >= 0.30:
    state = MEDIUM
else:
    state = LOW
```

#### חישוב `confidence`:
```
conf = 0.2 + 0.8 * evidence * stability * recency

evidence = sigmoid(n_completed_cycles / 2.0)  # מינימום 0.3
stability = 1.0 - (cycle_mad_days / cycle_mean_days)  # מינימום 0.2
recency = exp(-days_since_update / 60.0)  # מינימום 0.1
```

#### עדכון שבועי:
- **תהליך רקע** שרץ כל יום ב-00:00 UTC
- בודק לכל מוצר את יום היצירה שלו (מ-`inventory_log` הראשון)
- אם היום הנוכחי תואם ליום היצירה, מעדכן את `cycle_mean_days`:
  - מחשב את אורך המחזור הנצפה (מ-`cycle_started_at` עד EMPTY או PURCHASE חדש)
  - מעדכן `cycle_mean_days` בממוצע מצטבר
  - מעדכן `cycle_mad_days` (Mean Absolute Deviation)

#### טיפול בפעולות:
- **PURCHASE:** מתחיל מחזור חדש, `days_left = cycle_mean_days`
- **REPURCHASE:** כמו PURCHASE (יוצר PURCHASE שני)
- **TRASH:**
  - אם סיבה = "taste" או "expired": לא מעדכן `cycle_mean_days`, `days_left = 0`
  - אם סיבה = "ran out" או "empty": עדכון חלש מאוד (20% מ-`alpha_strong`)
- **EMPTY:** מחזור הושלם, עדכון `cycle_mean_days` בממוצע מצטבר

### 6. 📊 הרגלים (Habits)
- ניהול הרגלי אכילה וקניות
- מעקב אחר אירועים מיוחדים
- השפעה על מודל החיזוי

### 7. 📄 קבלות (Receipts)
- סריקת קבלות
- עיבוד אוטומטי של מוצרים
- עדכון מלאי אוטומטי

### 8. 💰 ניתוחים (Analytics)
- גרפים והוצאות
- ניתוח רווחיות

---

## 🗄️ מבנה Database

### טבלאות עיקריות:

#### `users`
- ניהול משתמשים (משולב עם Supabase Auth)

#### `products`
- מוצרים גלובליים (ללא `user_id`)
- `category_id` - שיוך לקטגוריה

#### `product_categories`
- קטגוריות מוצרים

#### `inventory`
- מלאי המשתמש
- `estimated_qty` - ימים שנותרו (days_left)
- `state` - FULL/MEDIUM/LOW/EMPTY
- `confidence` - רמת ביטחון של המודל

#### `inventory_log`
- לוג של כל הפעולות על המלאי
- `action` - PURCHASE/ADJUST/TRASH/EMPTY/REPURCHASE/CONSUME/RESET
- `source` - RECEIPT/SHOPPING_LIST/MANUAL/SYSTEM/RECIPE
- `note` - הערות וסיבות

#### `product_predictor_state`
- מצב המודל לכל מוצר
- `params` (JSONB) - כל הפרמטרים:
  - `cycle_mean_days` - ממוצע ימים למחזור
  - `cycle_mad_days` - סטייה ממוצעת
  - `cycle_started_at` - מתי התחיל המחזור הנוכחי
  - `last_pred_days_left` - חיזוי אחרון של ימים שנותרו
  - `n_completed_cycles` - מספר מחזורים שהושלמו
  - `n_strong_updates` - מספר עדכונים חזקים
  - `n_total_updates` - מספר עדכונים כולל
- `confidence` - רמת ביטחון

#### `inventory_forecasts`
- סנאפשוטים של חיזויים קודמים
- מעקב אחר היסטוריית חיזויים

#### `shopping_lists`
- רשימות קניות

#### `shopping_list_items`
- פריטים ברשימת קניות
- `sufficiency_marked` - האם סומן כמספיק
- `actual_qty_purchased` - כמות שנרכשה בפועל
- `qty_feedback` - פידבק על כמות (MORE/LESS)

#### `shopping_feedback_log`
- לוג של פידבק מהרשימת קניות
- `feedback_kind` - MORE/LESS
- `predicted_days_left` - חיזוי לפני
- `actual_days_left` - חיזוי אחרי

#### `habits`
- הרגלי משתמש

#### `receipts`
- קבלות

---

## 🔌 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - התחברות
- `POST /api/v1/auth/register` - הרשמה
- `POST /api/v1/auth/logout` - התנתקות

### Products
- `GET /api/v1/products` - קבלת כל המוצרים
- `POST /api/v1/products` - יצירת מוצר חדש
- `PUT /api/v1/products/{id}` - עדכון מוצר
- `DELETE /api/v1/products/{id}` - מחיקת מוצר

### Inventory
- `GET /api/v1/inventory` - קבלת מלאי המשתמש
- `POST /api/v1/inventory` - יצירת/עדכון פריט במלאי
- `PUT /api/v1/inventory/{product_id}` - עדכון פריט
- `POST /api/v1/inventory/{product_id}/action` - פעולה על מוצר (נזרק/נקנה מחדש/נגמר)
- `POST /api/v1/inventory/{product_id}/feedback` - פידבק על מוצר (MORE/LESS)

### Shopping Lists
- `GET /api/v1/shopping-lists` - קבלת רשימות קניות
- `POST /api/v1/shopping-lists` - יצירת רשימה חדשה
- `GET /api/v1/shopping-lists/{id}/items` - קבלת פריטים ברשימה
- `POST /api/v1/shopping-lists/{id}/items` - הוספת פריט לרשימה
- `PUT /api/v1/shopping-lists/{id}/items/{item_id}` - עדכון פריט
- `POST /api/v1/shopping-lists/{id}/complete` - השלמת רשימה

### Predictor
- `POST /api/v1/predictor/learn-from-shopping-feedback` - למידה מפידבק רשימת קניות
- `POST /api/v1/predictor/weekly-update` - עדכון שבועי ידני

### Recipes
- `POST /api/v1/recipes/generate` - יצירת מתכון
- `POST /api/v1/recipes/step-complete` - השלמת שלב בבישול

### Habits
- `GET /api/v1/habits` - קבלת הרגלים
- `POST /api/v1/habits` - יצירת הרגל

### Receipts
- `GET /api/v1/receipts` - קבלת קבלות
- `POST /api/v1/receipts` - יצירת קבלה

---

## 🔄 תהליכי רקע (Background Tasks)

### עדכון שבועי אוטומטי
- **תזמון:** כל יום ב-00:00 UTC
- **תהליך:**
  1. עבור כל משתמש וכל מוצר שלו
  2. מצא את יום היצירה של המוצר (מ-`inventory_log` הראשון)
  3. אם היום הנוכחי תואם ליום היצירה:
     - חשב את אורך המחזור הנצפה
     - עדכן `cycle_mean_days` בממוצע מצטבר
     - עדכן `cycle_mad_days`
     - עדכן `days_left` ו-`state` בהתאם

---

## 🎨 שיפורי UI/UX

### 1. **כיוון LTR ואנגלית**
- כל הממשק באנגלית
- כיוון LTR לכל העמודים
- `dir="ltr"` ב-`DashboardLayout`

### 2. **תצוגת מצבי מלאי**
- FULL (ירוק) - מלא
- MEDIUM (צהוב) - בינוני
- LOW (כתום) - נמוך
- EMPTY (אדום) - ריק

### 3. **פידבק ויזואלי**
- הדגשה של מוצרים שנוספו (רקע ירוק, ring)
- גלילה אוטומטית למוצר שנוסף
- הודעות toast להתראות

### 4. **חיפוש ואוטוקומפליט**
- חיפוש בזמן אמת ברשימת המוצרים
- הצעות אוטומטיות
- יצירת מוצר חדש ישירות מהחיפוש

### 5. **מצב בישול מודרך**
- תצוגה שלב אחר שלב
- סימון שלבים שהושלמו
- ניווט קדימה ואחורה
- עדכון מלאי בזמן אמת

---

## 🔧 שיפורים טכניים

### 1. **טיפול בשגיאות**
- טיפול בשגיאות datetime עם מיקרו-שניות לא עקביות
- Padding אוטומטי של מיקרו-שניות (5 ספרות → 6)
- Fallback ל-`dateutil.parser.isoparse`

### 2. **Type Safety**
- TypeScript strict mode
- Pydantic models לכל ה-schemas
- Validation מלא של inputs

### 3. **Logging**
- Logging מפורט לכל הפעולות
- Debug logs לבדיקת בעיות
- Error tracking

### 4. **Performance**
- Background tasks לעדכונים כבדים
- Indexing ב-database
- Caching של חישובים

---

## 📝 Migrations

### `add_repurchase_action.sql`
- הוספת `REPURCHASE` ל-`inventory_action` enum

### `add_shopping_item_feedback.sql`
- הוספת עמודות ל-`shopping_list_items`:
  - `sufficiency_marked`
  - `actual_qty_purchased`
  - `qty_feedback`
- יצירת טבלת `shopping_feedback_log`

### `add_recipe_source.sql`
- הוספת `RECIPE` ל-`inventory_source` enum

---

## 🐛 תיקוני באגים

### 1. **Category Filtering**
- תיקון גישה ל-`category_id` ב-frontend
- הסרת `response_model` מ-API כדי לשמור על מבנה nested

### 2. **Product Assignment**
- תיקון עדכון קטגוריה למוצר
- הבאת מוצר מחדש עם קטגוריה אחרי עדכון

### 3. **Days Left Update**
- תיקון עדכון `days_left` אחרי MORE/LESS feedback
- שימוש ב-`inventory_days_left` במקום חישוב מחדש

### 4. **Product Predictor State Update**
- עדכון `last_pred_days_left` ב-`product_predictor_state`
- עדכון `last_update_at`

### 5. **AI Confidence**
- מניעת ירידה ל-0
- מינימום confidence של 0.2
- שיפור חישוב evidence, stability, recency

### 6. **EMPTY Product Feedback**
- טיפול מיוחד ב-MORE/LESS על מוצר EMPTY
- MORE על EMPTY → מתחיל מחזור חדש עם `cycle_mean_days * 1.15`

### 7. **React Rendering Errors**
- המרת כל הערכים ל-strings לפני rendering
- טיפול ב-objects בתוך arrays

---

## 📚 קבצים חשובים

### Backend
- `app/main.py` - FastAPI app + background tasks
- `ema_cycle_predictor.py` - מודל החיזוי
- `app/services/predictor_service.py` - שירות החיזוי
- `app/api/inventory.py` - API endpoints למלאי
- `app/api/predictor.py` - API endpoints למודל
- `app/api/recipes.py` - API endpoints למתכונים
- `app/services/recipe_service.py` - שירות יצירת מתכונים

### Frontend
- `FRONT/src/app/dashboard/pantry/page.tsx` - עמוד מזווה
- `FRONT/src/app/dashboard/shopping/page.tsx` - עמוד רשימות קניות
- `FRONT/src/app/dashboard/shopping-active/page.tsx` - עמוד קנייה פעילה
- `FRONT/src/app/dashboard/recipes/page.tsx` - עמוד מתכונים
- `FRONT/src/components/layouts/DashboardLayout.tsx` - Layout ראשי

### Database
- `data_scheme.sql` - Schema מלא של ה-database
- `migrations/` - קבצי migration

---

## 🎯 סיכום

הפרויקט כולל:

✅ **מערכת מלאה לניהול מזווה** עם UI מתקדם  
✅ **מודל AI ללמידת דפוסי צריכה** עם עדכון שבועי  
✅ **רשימות קניות חכמות** עם חיזוי AI ופידבק  
✅ **מחולל מתכונים מבוסס GPT** עם מצב בישול מודרך  
✅ **עדכון אוטומטי של מלאי** מכל הפעולות  
✅ **תהליכי רקע** לעדכונים שבועיים  
✅ **UI/UX מקצועי** באנגלית ו-LTR  
✅ **Type safety מלא** עם TypeScript ו-Pydantic  
✅ **Error handling** מקצועי  
✅ **Logging מפורט** לניפוי באגים  

---

**הפרויקט מוכן לשימוש ומכיל את כל התכונות המבוקשות!** 🎉

