-- Create PHOTOS storage bucket for receipt images
-- Run this in Supabase SQL Editor

-- 1. Create the bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'PHOTOS',
    'PHOTOS',
    true,
    10485760,  -- 10MB limit
    ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic']
)
ON CONFLICT (id) DO UPDATE
SET public = true,
    file_size_limit = 10485760,
    allowed_mime_types = ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic'];

-- 2. Allow authenticated users to upload files
CREATE POLICY IF NOT EXISTS "Allow authenticated uploads to PHOTOS"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'PHOTOS');

-- 3. Allow everyone to read files (public bucket)
CREATE POLICY IF NOT EXISTS "Allow public read from PHOTOS"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'PHOTOS');

-- 4. Allow users to delete their own files
CREATE POLICY IF NOT EXISTS "Allow users to delete own files in PHOTOS"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'PHOTOS' 
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 5. Allow users to update their own files
CREATE POLICY IF NOT EXISTS "Allow users to update own files in PHOTOS"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'PHOTOS' 
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Verify bucket was created
SELECT * FROM storage.buckets WHERE id = 'PHOTOS';

