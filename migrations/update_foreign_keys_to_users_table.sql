-- Migration: Update all foreign keys from auth.users to public.users
-- This updates all tables to reference the new custom users table instead of auth.users
-- Run this in Supabase SQL Editor

-- Step 1: Drop all existing foreign key constraints that reference auth.users
DO $$
DECLARE
    r RECORD;
BEGIN
    -- Find all foreign key constraints that reference auth.users
    FOR r IN 
        SELECT 
            tc.table_schema, 
            tc.constraint_name, 
            tc.table_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' 
          AND ccu.table_name = 'users'
          AND ccu.table_schema = 'auth'
    LOOP
        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I', 
            r.table_schema, r.table_name, r.constraint_name);
        RAISE NOTICE 'Dropped constraint % from table %.%', r.constraint_name, r.table_schema, r.table_name;
    END LOOP;
END $$;

-- Step 2: Update each table to reference public.users(user_id) instead of auth.users(id)

-- Update profiles table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'profiles') THEN
        ALTER TABLE profiles 
        DROP CONSTRAINT IF EXISTS profiles_user_id_fkey;
        
        ALTER TABLE profiles 
        ADD CONSTRAINT profiles_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated profiles table foreign key';
    END IF;
END $$;

-- Update inventory table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'inventory') THEN
        ALTER TABLE inventory 
        DROP CONSTRAINT IF EXISTS inventory_user_id_fkey;
        
        ALTER TABLE inventory 
        ADD CONSTRAINT inventory_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated inventory table foreign key';
    END IF;
END $$;

-- Update receipts table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'receipts') THEN
        ALTER TABLE receipts 
        DROP CONSTRAINT IF EXISTS receipts_user_id_fkey;
        
        ALTER TABLE receipts 
        ADD CONSTRAINT receipts_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated receipts table foreign key';
    END IF;
END $$;

-- Update shopping_list table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'shopping_list') THEN
        ALTER TABLE shopping_list 
        DROP CONSTRAINT IF EXISTS shopping_list_user_id_fkey;
        
        ALTER TABLE shopping_list 
        ADD CONSTRAINT shopping_list_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated shopping_list table foreign key';
    END IF;
END $$;

-- Update inventory_log table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'inventory_log') THEN
        ALTER TABLE inventory_log 
        DROP CONSTRAINT IF EXISTS inventory_log_user_id_fkey;
        
        ALTER TABLE inventory_log 
        ADD CONSTRAINT inventory_log_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated inventory_log table foreign key';
    END IF;
END $$;

-- Update habits table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'habits') THEN
        ALTER TABLE habits 
        DROP CONSTRAINT IF EXISTS habits_user_id_fkey;
        
        ALTER TABLE habits 
        ADD CONSTRAINT habits_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated habits table foreign key';
    END IF;
END $$;

-- Update habit_inputs table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'habit_inputs') THEN
        ALTER TABLE habit_inputs 
        DROP CONSTRAINT IF EXISTS habit_inputs_user_id_fkey;
        
        ALTER TABLE habit_inputs 
        ADD CONSTRAINT habit_inputs_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated habit_inputs table foreign key';
    END IF;
END $$;

-- Update predictor_profiles table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'predictor_profiles') THEN
        ALTER TABLE predictor_profiles 
        DROP CONSTRAINT IF EXISTS predictor_profiles_user_id_fkey;
        
        ALTER TABLE predictor_profiles 
        ADD CONSTRAINT predictor_profiles_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated predictor_profiles table foreign key';
    END IF;
END $$;

-- Update product_predictor_state table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'product_predictor_state') THEN
        ALTER TABLE product_predictor_state 
        DROP CONSTRAINT IF EXISTS product_predictor_state_user_id_fkey;
        
        ALTER TABLE product_predictor_state 
        ADD CONSTRAINT product_predictor_state_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated product_predictor_state table foreign key';
    END IF;
END $$;

-- Update inventory_forecasts table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'inventory_forecasts') THEN
        ALTER TABLE inventory_forecasts 
        DROP CONSTRAINT IF EXISTS inventory_forecasts_user_id_fkey;
        
        ALTER TABLE inventory_forecasts 
        ADD CONSTRAINT inventory_forecasts_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated inventory_forecasts table foreign key';
    END IF;
END $$;

-- Step 3: Verify all foreign keys are updated
SELECT 
    tc.table_schema,
    tc.table_name,
    tc.constraint_name,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND ccu.table_name = 'users'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_name;

