-- Migration: Modify existing users table or create new one for custom authentication
-- This migration preserves all existing data and only adds/modifies columns as needed
-- Run this in Supabase SQL Editor

-- Step 1: Check if we're using auth.users or a custom users table
-- We'll work with a custom 'users' table (not auth.users which is managed by Supabase)

-- Step 2: Create users table if it doesn't exist, or modify if it does
DO $$
BEGIN
    -- Check if 'users' table exists
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'users') THEN
        -- Create new users table
        CREATE TABLE users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            username TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        
        RAISE NOTICE 'Created new users table';
    ELSE
        -- Table exists, add missing columns if needed
        
        -- Add hashed_password column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'hashed_password'
        ) THEN
            ALTER TABLE users ADD COLUMN hashed_password TEXT;
            RAISE NOTICE 'Added hashed_password column';
        END IF;
        
        -- Add username column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'username'
        ) THEN
            ALTER TABLE users ADD COLUMN username TEXT;
            RAISE NOTICE 'Added username column';
        END IF;
        
        -- Add created_at column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'created_at'
        ) THEN
            ALTER TABLE users ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
            RAISE NOTICE 'Added created_at column';
        END IF;
        
        -- Add updated_at column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'updated_at'
        ) THEN
            ALTER TABLE users ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
            RAISE NOTICE 'Added updated_at column';
        END IF;
        
        -- Ensure user_id is UUID if it exists, or add it
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'user_id'
        ) THEN
            -- Check if it's UUID type, if not, we might need to convert
            -- For now, just ensure it's the primary key
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'users_pkey'
            ) THEN
                ALTER TABLE users ADD PRIMARY KEY (user_id);
            END IF;
        ELSE
            -- Add user_id column
            ALTER TABLE users ADD COLUMN user_id UUID PRIMARY KEY DEFAULT gen_random_uuid();
            RAISE NOTICE 'Added user_id column';
        END IF;
        
        -- Ensure email is unique if it exists
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'email'
        ) THEN
            -- Check if unique constraint exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'users_email_key'
            ) THEN
                ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
                RAISE NOTICE 'Added unique constraint on email';
            END IF;
        END IF;
        
        RAISE NOTICE 'Modified existing users table';
    END IF;
END $$;

-- Step 3: Create index on email for faster lookups (if it doesn't exist)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Step 4: Create or replace updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Step 5: Create trigger for updated_at (drop and recreate to ensure it's correct)
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Step 6: If you have existing data in auth.users or profiles table that you want to migrate:
-- Uncomment and modify the following section if needed:

/*
-- Optional: Migrate data from auth.users to users table
-- Only run this if you want to copy existing users from Supabase Auth
INSERT INTO users (user_id, email, username, created_at, updated_at)
SELECT 
    id as user_id,
    email,
    raw_user_meta_data->>'username' as username,
    created_at,
    updated_at
FROM auth.users
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE users.email = auth.users.email
)
ON CONFLICT (email) DO NOTHING;
*/

/*
-- Optional: Migrate data from profiles table to users table
-- Only run this if you have a profiles table with user data
INSERT INTO users (user_id, email, username, created_at, updated_at)
SELECT 
    user_id,
    email,
    username,
    created_at,
    NOW() as updated_at
FROM profiles
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE users.user_id = profiles.user_id
)
ON CONFLICT (user_id) DO NOTHING;
*/

-- Step 7: Set default values for existing rows that might have NULL values
UPDATE users 
SET 
    created_at = COALESCE(created_at, NOW()),
    updated_at = COALESCE(updated_at, NOW())
WHERE created_at IS NULL OR updated_at IS NULL;

-- Final check: Show table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;

