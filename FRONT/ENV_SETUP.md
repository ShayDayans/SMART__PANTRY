# 🔧 הוראות הגדרת Environment Variables

## ⚠️ חשוב: כל משתמש צריך ליצור את הקובץ `.env.local`!

אם אתה מקבל שגיאת "Invalid API key", זה אומר שקובץ `.env.local` לא קיים או לא נכון.

---

## 📝 שלב 1: צור קובץ `.env.local`

צור קובץ חדש בשם `.env.local` בתיקיית `FRONT/` (לא בתיקיית השורש!)

### Windows (PowerShell):
```powershell
cd FRONT
New-Item -Path ".env.local" -ItemType File
```

### Windows (Command Prompt):
```cmd
cd FRONT
type nul > .env.local
```

### Mac/Linux:
```bash
cd FRONT
touch .env.local
```

---

## 📝 שלב 2: העתק את התוכן הבא לקובץ

פתח את הקובץ `.env.local` שיצרת והעתק את התוכן הבא:

```env
NEXT_PUBLIC_SUPABASE_URL=https://ceyynxrnsuggncjmpwhv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzNzE3OH0.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**⚠️ חשוב: העתק את ה-API key בדיוק כפי שהוא! כל תו חשוב!**

---

## 📝 שלב 3: שמור ובדוק

1. **שמור את הקובץ** (Ctrl+S)
2. **ודא שהקובץ נמצא בתיקיית `FRONT/`** (לא בתיקיית השורש!)
3. **עצור את השרת** (אם הוא רץ) - Ctrl+C
4. **נקה את ה-cache**:
   ```powershell
   cd FRONT
   Remove-Item -Path ".next" -Recurse -Force -ErrorAction SilentlyContinue
   ```
5. **הרץ מחדש**:
   ```powershell
   npm run dev
   ```

---

## ✅ איך לבדוק שזה עובד?

1. פתח את הדפדפן: http://localhost:3000/login
2. אם אתה רואה את דף ההתחברות בלי שגיאות = זה עובד! ✅
3. אם אתה עדיין רואה "Invalid API key":
   - בדוק שהקובץ `.env.local` קיים בתיקיית `FRONT/`
   - בדוק שה-API key נכון (העתק שוב מ-הקובץ הזה)
   - נקה את ה-cache והרץ מחדש

---

## 🔍 מיקום הקובץ

הקובץ צריך להיות כאן:
```
SMART__PANTRY/
  └── FRONT/
      └── .env.local  ← כאן!
```

**לא כאן:**
```
SMART__PANTRY/
  └── .env.local  ← לא כאן!
```

---

## 💡 טיפים

- **הקובץ `.env.local` לא נשמר ב-Git** (זה בסדר, כל משתמש צריך ליצור אותו)
- **אם אתה עובד על כמה מחשבים** - תצטרך ליצור את הקובץ בכל מחשב
- **אם אתה משתף את הפרויקט** - תזכור לספר למשתמש השני ליצור את הקובץ!

---

## 🆘 עדיין לא עובד?

1. **בדוק את הקונסול** (F12 בדפדפן) - אולי יש שגיאה אחרת
2. **בדוק את הטרמינל** - אולי יש שגיאת compilation
3. **נסה ליצור את הקובץ מחדש** - אולי יש שגיאת העתקה
4. **בדוק שה-API key נכון** - העתק שוב מ-הקובץ הזה

