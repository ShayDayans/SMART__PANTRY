-- Migration: Migrate data from auth.users to public.users and update foreign keys
-- This handles existing data and ensures all foreign keys point to the new users table
-- Run this in Supabase SQL Editor

-- Step 1: Check if users table exists, if not create it
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'users') THEN
        CREATE TABLE users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL DEFAULT 'temp_password_needs_reset',
            username TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        RAISE NOTICE 'Created users table';
    END IF;
END $$;

-- Step 2: Migrate users from auth.users to public.users (if auth.users exists and has data)
DO $$
DECLARE
    auth_user_count INTEGER;
    migrated_count INTEGER := 0;
BEGIN
    -- Check if auth.users exists and has data
    SELECT COUNT(*) INTO auth_user_count
    FROM information_schema.tables 
    WHERE table_schema = 'auth' AND table_name = 'users';
    
    IF auth_user_count > 0 THEN
        -- Migrate users from auth.users to public.users
        -- We'll use the auth.users id as the user_id in the new table
        -- Note: hashed_password is required, so we'll set a placeholder that needs to be reset
        INSERT INTO public.users (user_id, email, hashed_password, username, created_at, updated_at)
        SELECT 
            id as user_id,
            email,
            '$2b$12$placeholder_hash_for_migrated_user_needs_reset' as hashed_password,
            COALESCE(raw_user_meta_data->>'username', raw_user_meta_data->>'name') as username,
            created_at,
            COALESCE(updated_at, created_at) as updated_at
        FROM auth.users
        WHERE NOT EXISTS (
            SELECT 1 FROM public.users WHERE public.users.user_id = auth.users.id
        )
        ON CONFLICT (user_id) DO NOTHING;
        
        GET DIAGNOSTICS migrated_count = ROW_COUNT;
        RAISE NOTICE 'Migrated % users from auth.users to public.users', migrated_count;
    ELSE
        RAISE NOTICE 'auth.users table does not exist or is empty';
    END IF;
END $$;

-- Step 3: For any existing data in other tables with user_id not in users table,
-- we need to either:
-- a) Create placeholder users, or
-- b) Delete the orphaned data, or  
-- c) Update the user_id to match existing users

-- Option: Create placeholder users for orphaned data
DO $$
DECLARE
    orphaned_user RECORD;
    new_user_id UUID;
BEGIN
    -- Find user_ids in inventory that don't exist in users
    FOR orphaned_user IN 
        SELECT DISTINCT i.user_id
        FROM inventory i
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.user_id = i.user_id
        )
    LOOP
        -- Create a placeholder user
        INSERT INTO users (user_id, email, hashed_password, username, created_at, updated_at)
        VALUES (
            orphaned_user.user_id,
            'migrated_' || orphaned_user.user_id::text || '@migrated.local',
            '$2b$12$placeholder_hash_for_migrated_user',
            'Migrated User',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;
        
        RAISE NOTICE 'Created placeholder user for orphaned user_id: %', orphaned_user.user_id;
    END LOOP;
    
    -- Repeat for other tables
    FOR orphaned_user IN 
        SELECT DISTINCT r.user_id
        FROM receipts r
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.user_id = r.user_id
        )
    LOOP
        INSERT INTO users (user_id, email, hashed_password, username, created_at, updated_at)
        VALUES (
            orphaned_user.user_id,
            'migrated_' || orphaned_user.user_id::text || '@migrated.local',
            '$2b$12$placeholder_hash_for_migrated_user',
            'Migrated User',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;
    END LOOP;
    
    FOR orphaned_user IN 
        SELECT DISTINCT sl.user_id
        FROM shopping_list sl
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.user_id = sl.user_id
        )
    LOOP
        INSERT INTO users (user_id, email, hashed_password, username, created_at, updated_at)
        VALUES (
            orphaned_user.user_id,
            'migrated_' || orphaned_user.user_id::text || '@migrated.local',
            '$2b$12$placeholder_hash_for_migrated_user',
            'Migrated User',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;
    END LOOP;
    
    FOR orphaned_user IN 
        SELECT DISTINCT il.user_id
        FROM inventory_log il
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.user_id = il.user_id
        )
    LOOP
        INSERT INTO users (user_id, email, hashed_password, username, created_at, updated_at)
        VALUES (
            orphaned_user.user_id,
            'migrated_' || orphaned_user.user_id::text || '@migrated.local',
            '$2b$12$placeholder_hash_for_migrated_user',
            'Migrated User',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;
    END LOOP;
    
    FOR orphaned_user IN 
        SELECT DISTINCT h.user_id
        FROM habits h
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.user_id = h.user_id
        )
    LOOP
        INSERT INTO users (user_id, email, hashed_password, username, created_at, updated_at)
        VALUES (
            orphaned_user.user_id,
            'migrated_' || orphaned_user.user_id::text || '@migrated.local',
            '$2b$12$placeholder_hash_for_migrated_user',
            'Migrated User',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;
    END LOOP;
    
    FOR orphaned_user IN 
        SELECT DISTINCT hi.user_id
        FROM habit_inputs hi
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.user_id = hi.user_id
        )
    LOOP
        INSERT INTO users (user_id, email, hashed_password, username, created_at, updated_at)
        VALUES (
            orphaned_user.user_id,
            'migrated_' || orphaned_user.user_id::text || '@migrated.local',
            '$2b$12$placeholder_hash_for_migrated_user',
            'Migrated User',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;
    END LOOP;
    
    FOR orphaned_user IN 
        SELECT DISTINCT pp.user_id
        FROM predictor_profiles pp
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.user_id = pp.user_id
        )
    LOOP
        INSERT INTO users (user_id, email, hashed_password, username, created_at, updated_at)
        VALUES (
            orphaned_user.user_id,
            'migrated_' || orphaned_user.user_id::text || '@migrated.local',
            '$2b$12$placeholder_hash_for_migrated_user',
            'Migrated User',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;
    END LOOP;
    
    FOR orphaned_user IN 
        SELECT DISTINCT pps.user_id
        FROM product_predictor_state pps
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.user_id = pps.user_id
        )
    LOOP
        INSERT INTO users (user_id, email, hashed_password, username, created_at, updated_at)
        VALUES (
            orphaned_user.user_id,
            'migrated_' || orphaned_user.user_id::text || '@migrated.local',
            '$2b$12$placeholder_hash_for_migrated_user',
            'Migrated User',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;
    END LOOP;
    
    FOR orphaned_user IN 
        SELECT DISTINCT inf.user_id
        FROM inventory_forecasts inf
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.user_id = inf.user_id
        )
    LOOP
        INSERT INTO users (user_id, email, hashed_password, username, created_at, updated_at)
        VALUES (
            orphaned_user.user_id,
            'migrated_' || orphaned_user.user_id::text || '@migrated.local',
            '$2b$12$placeholder_hash_for_migrated_user',
            'Migrated User',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;
    END LOOP;
END $$;

-- Step 4: Now update all foreign keys (this should work now that all user_ids exist)
-- Drop old constraints first
DO $$
DECLARE
    r RECORD;
BEGIN
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
          AND (
            (ccu.table_name = 'users' AND ccu.table_schema = 'auth')
            OR (ccu.table_name = 'users' AND ccu.table_schema = 'public' AND tc.constraint_name LIKE '%_user_id_fkey')
          )
    LOOP
        BEGIN
            EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I', 
                r.table_schema, r.table_name, r.constraint_name);
            RAISE NOTICE 'Dropped constraint % from table %.%', r.constraint_name, r.table_schema, r.table_name;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Could not drop constraint % from table %.%: %', r.constraint_name, r.table_schema, r.table_name, SQLERRM;
        END;
    END LOOP;
END $$;

-- Step 5: Add new foreign key constraints pointing to public.users(user_id)
DO $$
BEGIN
    -- Update profiles
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'profiles') THEN
        ALTER TABLE profiles 
        DROP CONSTRAINT IF EXISTS profiles_user_id_fkey;
        
        ALTER TABLE profiles 
        ADD CONSTRAINT profiles_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated profiles table foreign key';
    END IF;
    
    -- Update inventory
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'inventory') THEN
        ALTER TABLE inventory 
        DROP CONSTRAINT IF EXISTS inventory_user_id_fkey;
        
        ALTER TABLE inventory 
        ADD CONSTRAINT inventory_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated inventory table foreign key';
    END IF;
    
    -- Update receipts
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'receipts') THEN
        ALTER TABLE receipts 
        DROP CONSTRAINT IF EXISTS receipts_user_id_fkey;
        
        ALTER TABLE receipts 
        ADD CONSTRAINT receipts_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated receipts table foreign key';
    END IF;
    
    -- Update shopping_list
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'shopping_list') THEN
        ALTER TABLE shopping_list 
        DROP CONSTRAINT IF EXISTS shopping_list_user_id_fkey;
        
        ALTER TABLE shopping_list 
        ADD CONSTRAINT shopping_list_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated shopping_list table foreign key';
    END IF;
    
    -- Update inventory_log
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'inventory_log') THEN
        ALTER TABLE inventory_log 
        DROP CONSTRAINT IF EXISTS inventory_log_user_id_fkey;
        
        ALTER TABLE inventory_log 
        ADD CONSTRAINT inventory_log_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated inventory_log table foreign key';
    END IF;
    
    -- Update habits
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'habits') THEN
        ALTER TABLE habits 
        DROP CONSTRAINT IF EXISTS habits_user_id_fkey;
        
        ALTER TABLE habits 
        ADD CONSTRAINT habits_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated habits table foreign key';
    END IF;
    
    -- Update habit_inputs
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'habit_inputs') THEN
        ALTER TABLE habit_inputs 
        DROP CONSTRAINT IF EXISTS habit_inputs_user_id_fkey;
        
        ALTER TABLE habit_inputs 
        ADD CONSTRAINT habit_inputs_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated habit_inputs table foreign key';
    END IF;
    
    -- Update predictor_profiles
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'predictor_profiles') THEN
        ALTER TABLE predictor_profiles 
        DROP CONSTRAINT IF EXISTS predictor_profiles_user_id_fkey;
        
        ALTER TABLE predictor_profiles 
        ADD CONSTRAINT predictor_profiles_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated predictor_profiles table foreign key';
    END IF;
    
    -- Update product_predictor_state
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'product_predictor_state') THEN
        ALTER TABLE product_predictor_state 
        DROP CONSTRAINT IF EXISTS product_predictor_state_user_id_fkey;
        
        ALTER TABLE product_predictor_state 
        ADD CONSTRAINT product_predictor_state_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated product_predictor_state table foreign key';
    END IF;
    
    -- Update inventory_forecasts
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'inventory_forecasts') THEN
        ALTER TABLE inventory_forecasts 
        DROP CONSTRAINT IF EXISTS inventory_forecasts_user_id_fkey;
        
        ALTER TABLE inventory_forecasts 
        ADD CONSTRAINT inventory_forecasts_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Updated inventory_forecasts table foreign key';
    END IF;
    
    RAISE NOTICE 'All foreign keys updated successfully';
END $$;

-- Step 6: Verify all foreign keys
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
  AND ccu.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_name;

