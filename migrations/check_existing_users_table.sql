-- Check existing users table structure
-- Run this FIRST to see what columns already exist

-- Check if users table exists
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = 'users'
        ) THEN 'users table EXISTS'
        ELSE 'users table DOES NOT EXIST'
    END as table_status;

-- If table exists, show its structure
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'users' 
    AND table_schema = 'public'
ORDER BY ordinal_position;

-- Show constraints
SELECT 
    conname as constraint_name,
    contype as constraint_type,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint
WHERE conrelid = 'public.users'::regclass;

-- Check if there's data in the table
SELECT COUNT(*) as row_count FROM users;

