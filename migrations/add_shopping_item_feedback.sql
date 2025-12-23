-- Migration: Add feedback fields to shopping_list_items table
-- Run this in Supabase SQL Editor

-- Add new columns for quantity feedback
ALTER TABLE shopping_list_items
ADD COLUMN IF NOT EXISTS sufficiency_marked BOOLEAN,
ADD COLUMN IF NOT EXISTS actual_qty_purchased NUMERIC,
ADD COLUMN IF NOT EXISTS qty_feedback TEXT;

-- Add comment for documentation
COMMENT ON COLUMN shopping_list_items.sufficiency_marked IS 'User marked if quantity is sufficient until next shopping';
COMMENT ON COLUMN shopping_list_items.actual_qty_purchased IS 'Actual quantity purchased (may differ from recommended_qty)';
COMMENT ON COLUMN shopping_list_items.qty_feedback IS 'Feedback: LESS, MORE, EXACT, NOT_ENOUGH';

