# Migration Guide: Custom Users Table

## סקירה כללית

המיגרציה הזו מעבירה את כל הטבלאות מהתייחסות ל-`auth.users(id)` ל-`public.users(user_id)`.

## טבלאות שמעודכנות

המיגרציה מעדכנת את כל הטבלאות הבאות:

1. ✅ **profiles** - `user_id` → `public.users(user_id)`
2. ✅ **inventory** - `user_id` → `public.users(user_id)`
3. ✅ **receipts** - `user_id` → `public.users(user_id)`
4. ✅ **shopping_list** - `user_id` → `public.users(user_id)`
5. ✅ **inventory_log** - `user_id` → `public.users(user_id)`
6. ✅ **habits** - `user_id` → `public.users(user_id)`
7. ✅ **habit_inputs** - `user_id` → `public.users(user_id)`
8. ✅ **predictor_profiles** - `user_id` → `public.users(user_id)`
9. ✅ **product_predictor_state** - `user_id` → `public.users(user_id)`
10. ✅ **inventory_forecasts** - `user_id` → `public.users(user_id)`

## איך להריץ את המיגרציה

### שלב 1: הרץ את המיגרציה הראשית
הרץ את `migrations/migrate_data_to_new_users_table.sql` ב-Supabase SQL Editor.

סקריפט זה:
- יוצר את טבלת `users` אם היא לא קיימת
- מעתיק משתמשים מ-`auth.users` ל-`public.users` (אם קיימים)
- יוצר placeholder users לכל ה-`user_id` הקיימים בטבלאות האחרות
- מוחק את כל ה-foreign keys הישנים
- יוצר מחדש את כל ה-foreign keys להצביע על `public.users(user_id)`

### שלב 2: בדוק שהכל עבד
הרץ את `migrations/verify_all_foreign_keys.sql` ב-Supabase SQL Editor.

סקריפט זה יציג:
- רשימה של כל ה-foreign keys עם סטטוס (✅ CORRECT / ❌ OLD)
- ספירה של כמה foreign keys נכונים וכמה ישנים
- רשימה של כל הטבלאות שצריכות foreign keys

## מה לעשות אם יש בעיות

אם יש foreign keys שעדיין מצביעים על `auth.users`:
1. הרץ שוב את `migrations/migrate_data_to_new_users_table.sql`
2. או הרץ את `migrations/update_foreign_keys_to_users_table.sql` (סקריפט פשוט יותר שמעדכן רק foreign keys)

## הערות חשובות

- **נתונים קיימים**: המיגרציה שומרת על כל הנתונים הקיימים
- **Placeholder users**: משתמשים שהועתקו מ-`auth.users` יקבלו placeholder password hash. הם יצטרכו לאפס את הסיסמה דרך ה-API או ידנית
- **Foreign keys**: כל ה-foreign keys מעודכנים ל-`ON DELETE CASCADE` - אם משתמש נמחק, כל הנתונים שלו נמחקים אוטומטית

