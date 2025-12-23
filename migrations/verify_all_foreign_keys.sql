-- Verification Script: Check all foreign keys pointing to users table
-- This script verifies that all tables correctly reference public.users(user_id)
-- Run this in Supabase SQL Editor to see the current state

-- Step 1: Show all foreign keys that reference ANY users table (auth or public)
SELECT 
    tc.table_schema,
    tc.table_name,
    tc.constraint_name,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    CASE 
        WHEN ccu.table_schema = 'public' AND ccu.table_name = 'users' AND ccu.column_name = 'user_id' THEN '✅ CORRECT'
        WHEN ccu.table_schema = 'auth' AND ccu.table_name = 'users' THEN '❌ OLD (needs update)'
        ELSE '⚠️ UNKNOWN'
    END AS status
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND ccu.table_name = 'users'
ORDER BY 
    CASE 
        WHEN ccu.table_schema = 'public' AND ccu.table_name = 'users' AND ccu.column_name = 'user_id' THEN 1
        ELSE 2
    END,
    tc.table_name, 
    tc.constraint_name;

-- Step 2: Count foreign keys by status
SELECT 
    CASE 
        WHEN ccu.table_schema = 'public' AND ccu.table_name = 'users' AND ccu.column_name = 'user_id' THEN '✅ Correct (public.users.user_id)'
        WHEN ccu.table_schema = 'auth' AND ccu.table_name = 'users' THEN '❌ Old (auth.users.id)'
        ELSE '⚠️ Unknown'
    END AS status,
    COUNT(*) AS count
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND ccu.table_name = 'users'
GROUP BY 
    CASE 
        WHEN ccu.table_schema = 'public' AND ccu.table_name = 'users' AND ccu.column_name = 'user_id' THEN '✅ Correct (public.users.user_id)'
        WHEN ccu.table_schema = 'auth' AND ccu.table_name = 'users' THEN '❌ Old (auth.users.id)'
        ELSE '⚠️ Unknown'
    END;

-- Step 3: List all tables that should have user_id foreign keys (from data_scheme.sql)
-- This helps identify if any tables are missing foreign keys
SELECT 
    'profiles' AS expected_table,
    EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'profiles' 
        AND constraint_name LIKE '%user_id%'
    ) AS has_foreign_key
UNION ALL
SELECT 'inventory', EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_name = 'inventory' 
    AND constraint_name LIKE '%user_id%'
)
UNION ALL
SELECT 'receipts', EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_name = 'receipts' 
    AND constraint_name LIKE '%user_id%'
)
UNION ALL
SELECT 'shopping_list', EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_name = 'shopping_list' 
    AND constraint_name LIKE '%user_id%'
)
UNION ALL
SELECT 'inventory_log', EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_name = 'inventory_log' 
    AND constraint_name LIKE '%user_id%'
)
UNION ALL
SELECT 'habits', EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_name = 'habits' 
    AND constraint_name LIKE '%user_id%'
)
UNION ALL
SELECT 'habit_inputs', EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_name = 'habit_inputs' 
    AND constraint_name LIKE '%user_id%'
)
UNION ALL
SELECT 'predictor_profiles', EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_name = 'predictor_profiles' 
    AND constraint_name LIKE '%user_id%'
)
UNION ALL
SELECT 'product_predictor_state', EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_name = 'product_predictor_state' 
    AND constraint_name LIKE '%user_id%'
)
UNION ALL
SELECT 'inventory_forecasts', EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE table_name = 'inventory_forecasts' 
    AND constraint_name LIKE '%user_id%'
);

