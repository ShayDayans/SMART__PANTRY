# פתרון בעיות - פרונטאנד

## שגיאת 404

אם אתה מקבל שגיאת 404, נסה:

1. **ודא שהשרת רץ:**
   ```bash
   npm run dev
   ```
   אתה אמור לראות:
   ```
   ▲ Next.js 14.x.x
   - Local:        http://localhost:3000
   ```

2. **בדוק את דף הבדיקה:**
   פתח: http://localhost:3000/test
   
   אם הדף הזה עובד, הבעיה היא ב-routing של דפים אחרים.

3. **ודא שקובץ .env.local קיים:**
   צור קובץ `.env.local` בתיקיית השורש עם:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://ceyynxrnsuggncjmpwhv.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzMzcxNzh9.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **נקה את ה-cache:**
   ```bash
   rm -rf .next
   npm run dev
   ```
   (ב-Windows: `rmdir /s /q .next` ואז `npm run dev`)

5. **בדוק שגיאות בקונסול:**
   - פתח את DevTools (F12)
   - לך לטאב Console
   - חפש שגיאות אדומות

6. **בדוק שגיאות בטרמינל:**
   - חפש הודעות שגיאה בטרמינל של Next.js
   - שגיאות נפוצות:
     - `Module not found` - צריך להריץ `npm install`
     - `Cannot find module` - בדוק את ה-imports
     - `Environment variable not found` - ודא ש-.env.local קיים

## שגיאות נפוצות

### "Module not found: Can't resolve '@/...'"
**פתרון:** ודא ש-`tsconfig.json` מכיל:
```json
"paths": {
  "@/*": ["./src/*"]
}
```

### "Supabase client error"
**פתרון:** ודא ש-.env.local מכיל את הערכים הנכונים של Supabase

### "Hydration error"
**פתרון:** זה קורה כשיש הבדלים בין server ו-client. בדוק את הקוד ב-components

## בדיקת קישורים

- http://localhost:3000/ - דף ראשי
- http://localhost:3000/test - דף בדיקה
- http://localhost:3000/login - דף התחברות
- http://localhost:3000/dashboard - דשבורד (דורש התחברות)

## אם כלום לא עובד

1. עצור את השרת (Ctrl+C)
2. מחק את התיקייה `.next`:
   ```bash
   rmdir /s /q .next
   ```
3. התקן מחדש תלויות:
   ```bash
   npm install
   ```
4. הרץ שוב:
   ```bash
   npm run dev
   ```

