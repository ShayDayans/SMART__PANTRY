# מדריך התחברות לפיתוח - Development Login Guide

## בעיה: "Invalid login credentials" או "Email rate limit exceeded"

**למה זה קורה?**
- Supabase מגביל את שליחת האימיילים ל-**2 אימיילים לשעה** (ברירת מחדל)
- כדי לשנות את המגבלה, צריך להגדיר **SMTP מותאם אישית**
- זה מגביל מאוד לפיתוח!

**הפתרון הכי מהיר לפיתוח:**
1. **השבת email confirmation** (לא צריך אימיילים בכלל)
2. **צור משתמשים ידנית** (לא צריך אימיילים בכלל)

אם אתה מקבל שגיאות אלו, יש כמה פתרונות מהירים:

---

## פתרון 1: יצירת משתמש ידנית ב-Supabase Dashboard (הכי מהיר!)

### שלבים:

1. **היכנס ל-Supabase Dashboard**
   - לך ל: https://supabase.com/dashboard
   - בחר את הפרויקט שלך

2. **נווט ל-Authentication → Users**
   - בתפריט השמאלי, לחץ על "Authentication"
   - לחץ על "Users"

3. **צור משתמש חדש**
   - לחץ על כפתור "Add User" או "Create User"
   - מלא את הפרטים:
     - **Email**: הכנס אימייל (למשל: `dev@test.com`)
     - **Password**: הכנס סיסמה (למשל: `password123`)
     - **Auto Confirm User**: ✅ סמן את זה! (כך לא צריך אימות אימייל)
   - לחץ "Create User"

4. **התחבר עם הפרטים שיצרת**
   - חזור לאפליקציה
   - הכנס את האימייל והסיסמה שיצרת
   - לחץ "Sign In"

✅ **זה אמור לעבוד מיד!**

---

## פתרון 2: השבתת אימות אימייל (לפיתוח)

### שלבים:

1. **היכנס ל-Supabase Dashboard**
   - לך ל: https://supabase.com/dashboard
   - בחר את הפרויקט שלך

2. **נווט ל-Authentication → Settings**
   - בתפריט השמאלי, לחץ על "Authentication"
   - לחץ על "Settings" או "Configuration"

3. **השבת Email Confirmation**
   - מצא את "Enable email confirmations"
   - **הסר את הסימון** (השבית את זה)
   - או מצא "Auto Confirm" והגדר ל-`true`
   - שמור את השינויים

4. **עכשיו תוכל להרשם בלי אימייל אימות**
   - חזור לאפליקציה
   - לחץ "Sign Up"
   - מלא פרטים והרשם
   - המשתמש יווצר מיד ויוכל להתחבר

---

## פתרון 3: איפוס סיסמה (אם המשתמש כבר קיים)

### שלבים:

1. **היכנס ל-Supabase Dashboard**
   - לך ל: https://supabase.com/dashboard
   - בחר את הפרויקט שלך

2. **נווט ל-Authentication → Users**
   - בתפריט השמאלי, לחץ על "Authentication"
   - לחץ על "Users"

3. **מצא את המשתמש ולחץ עליו**
   - לחץ על המשתמש שברצונך לאפס את הסיסמה שלו

4. **אפס סיסמה**
   - לחץ על "Reset Password" או "Change Password"
   - הכנס סיסמה חדשה
   - שמור

5. **התחבר עם הסיסמה החדשה**

---

## פתרון 4: בדיקת Auth Logs

אם שום דבר לא עובד, בדוק את ה-Logs:

1. **היכנס ל-Supabase Dashboard**
   - לך ל: https://supabase.com/dashboard
   - בחר את הפרויקט שלך

2. **נווט ל-Authentication → Logs**
   - בתפריט השמאלי, לחץ על "Authentication"
   - לחץ על "Logs"
   - בדוק את השגיאות והפרטים

---

## למה אני לא יכול לשנות את ה-Rate Limit?

**הסיבה:**
- Supabase מגביל את שליחת האימיילים ל-**2 אימיילים לשעה** (ברירת מחדל)
- כדי לשנות את המגבלה, צריך להגדיר **SMTP מותאם אישית** (Custom SMTP)
- זה אומר שאתה צריך לספק שירות SMTP משלך (Gmail, SendGrid, Mailgun וכו')

**למה Supabase עושה את זה?**
- כדי למנוע spam
- כדי לחסוך בעלויות
- כדי לעודד שימוש ב-SMTP מותאם אישית ל-production

**הפתרון לפיתוח:**
- **אל תשתמש באימיילים בכלל!**
- השבת email confirmation
- צור משתמשים ידנית
- כך תוכל לפתח בלי בעיות

**הפתרון ל-Production:**
- הגדר SMTP מותאם אישית
- כך תוכל לשלוח יותר אימיילים
- כך תוכל לשלוט במגבלות

---

## איך להגדיר SMTP מותאם אישית (אופציונלי)

אם אתה רוצה להגדיר SMTP משלך:

1. **היכנס ל-Supabase Dashboard**
   - לך ל: https://supabase.com/dashboard
   - בחר את הפרויקט שלך

2. **נווט ל-Authentication → Settings → SMTP Settings**
   - בתפריט השמאלי, לחץ על "Authentication"
   - לחץ על "Settings"
   - מצא "SMTP Settings"

3. **הגדר SMTP**
   - בחר ספק SMTP (Gmail, SendGrid, Mailgun וכו')
   - מלא את הפרטים:
     - SMTP Host
     - SMTP Port
     - SMTP User
     - SMTP Password
   - שמור

4. **עכשיו תוכל לשנות את ה-Rate Limit**
   - לך ל-Settings → Rate Limits
   - תוכל לשנות את המגבלה של "sending emails"

**שירותי SMTP מומלצים:**
- **Gmail**: חינם, עד 500 אימיילים ביום
- **SendGrid**: חינם, עד 100 אימיילים ביום
- **Mailgun**: חינם, עד 5,000 אימיילים בחודש
- **AWS SES**: זול מאוד, תשלום לפי שימוש

---

## המלצה לפיתוח

**הפתרון הכי מהיר והכי נוח לפיתוח:**
1. השבת email confirmation (פתרון 2)
2. צור משתמש ידנית (פתרון 1)
3. התחבר עם הפרטים שיצרת

כך תוכל לפתח בלי בעיות של rate limit או אימות אימייל!

---

## לפני Production

⚠️ **חשוב!** לפני שתעלה ל-production:
- החזר את email confirmation
- הסר משתמשי בדיקה
- ודא שהכל מאובטח

---

## קישורים שימושיים

- Supabase Dashboard: https://supabase.com/dashboard
- Authentication Settings: https://supabase.com/dashboard/project/YOUR_PROJECT/auth/users
- Auth Logs: https://supabase.com/dashboard/project/YOUR_PROJECT/auth/logs

---

## Project Reference

הפרויקט שלך: `ceyynxrnsuggncjmpwhv`

