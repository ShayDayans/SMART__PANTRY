# הוראות התקנה לפרונטאנד

## 1. יצירת קובץ .env.local

**⚠️ חשוב: כל משתמש צריך ליצור את הקובץ `.env.local` בתיקיית `FRONT/`!**

יש שתי אפשרויות:

### אפשרות 1: העתקה מקובץ דוגמה (מומלץ)
```bash
cd FRONT
copy .env.local.example .env.local
```

### אפשרות 2: יצירה ידנית
צור קובץ `.env.local` בתיקיית `FRONT/` עם התוכן הבא:

```env
NEXT_PUBLIC_SUPABASE_URL=https://ceyynxrnsuggncjmpwhv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzNzE3OH0.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## 2. התקנת תלויות

```bash
npm install
```

## 3. הרצת השרת

```bash
npm run dev
```

השרת יעלה על http://localhost:3000

## 4. פתרון בעיות

### שגיאת "Invalid API key":
1. **ודא שקובץ `.env.local` קיים בתיקיית `FRONT/`** (לא בתיקיית השורש!)
2. **ודא שה-API key נכון** - העתק מ-`.env.local.example` או מ-`SETUP_FRONTEND.md`
3. **עצור את השרת** (Ctrl+C) והרץ שוב `npm run dev`
4. **נקה את ה-cache**:
   ```bash
   cd FRONT
   Remove-Item -Path ".next" -Recurse -Force -ErrorAction SilentlyContinue
   npm run dev
   ```

### שגיאת 404:
1. ודא שהשרת רץ (`npm run dev`)
2. ודא שקובץ `.env.local` קיים עם הערכים הנכונים
3. עצור את השרת (Ctrl+C) והרץ שוב `npm run dev`
4. בדוק את הקונסול לדפדפן (F12) לשגיאות

## קישורים

- דף התחברות: http://localhost:3000/login
- דף ראשי: http://localhost:3000/
- דשבורד: http://localhost:3000/dashboard

