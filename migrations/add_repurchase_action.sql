-- Migration: Add REPURCHASE to inventory_action enum
-- Run this in Supabase SQL Editor

-- Add REPURCHASE to existing enum if it doesn't exist
DO $$ 
BEGIN
    -- Check if REPURCHASE already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'REPURCHASE' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'inventory_action')
    ) THEN
        ALTER TYPE inventory_action ADD VALUE 'REPURCHASE';
        RAISE NOTICE 'Added REPURCHASE to inventory_action enum';
    ELSE
        RAISE NOTICE 'REPURCHASE already exists in inventory_action enum';
    END IF;
END $$;

