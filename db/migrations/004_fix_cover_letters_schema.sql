-- ============================================================================
-- Fix Cover Letters Table Schema
-- ============================================================================
-- Add missing 'content' column to cover_letters table

-- Add content column if it doesn't exist
ALTER TABLE cover_letters 
ADD COLUMN IF NOT EXISTS content TEXT;

-- Also ensure file_path column exists
ALTER TABLE cover_letters 
ADD COLUMN IF NOT EXISTS file_path TEXT;

-- Verify the table structure
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'cover_letters';
