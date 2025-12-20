-- Create PHOTOS storage bucket for receipt images
-- Run this in Supabase SQL Editor

-- 1. Create the bucket (if not exists)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'PHOTOS',
    'PHOTOS',
    true,
    10485760,
    ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic']
)
ON CONFLICT (id) DO UPDATE
SET public = true,
    file_size_limit = 10485760,
    allowed_mime_types = ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic'];

-- 2. Drop existing policies (ignore errors if they don't exist)
DROP POLICY IF EXISTS "Allow authenticated uploads to PHOTOS" ON storage.objects;
DROP POLICY IF EXISTS "Allow public read from PHOTOS" ON storage.objects;
DROP POLICY IF EXISTS "Allow users to delete own files in PHOTOS" ON storage.objects;
DROP POLICY IF EXISTS "Allow users to update own files in PHOTOS" ON storage.objects;

-- 3. Create new policies
CREATE POLICY "Allow authenticated uploads to PHOTOS"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'PHOTOS');

CREATE POLICY "Allow public read from PHOTOS"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'PHOTOS');

CREATE POLICY "Allow users to delete own files in PHOTOS"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'PHOTOS' 
    AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Allow users to update own files in PHOTOS"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'PHOTOS' 
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 4. Verify bucket was created
SELECT id, name, public, file_size_limit FROM storage.buckets WHERE id = 'PHOTOS';

