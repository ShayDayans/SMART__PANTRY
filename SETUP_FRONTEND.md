# הוראות התקנה לפרונטאנד

## 1. יצירת קובץ .env.local

צור קובץ `.env.local` בתיקיית השורש של הפרויקט עם התוכן הבא:

```env
NEXT_PUBLIC_SUPABASE_URL=https://ceyynxrnsuggncjmpwhv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzMzcxNzh9.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k
NEXT_PUBLIC_API_URL=http://localhost:8000
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

אם אתה מקבל שגיאת 404:

1. ודא שהשרת רץ (`npm run dev`)
2. ודא שקובץ `.env.local` קיים עם הערכים הנכונים
3. עצור את השרת (Ctrl+C) והרץ שוב `npm run dev`
4. בדוק את הקונסול לדפדפן (F12) לשגיאות

## קישורים

- דף התחברות: http://localhost:3000/login
- דף ראשי: http://localhost:3000/
- דשבורד: http://localhost:3000/dashboard

