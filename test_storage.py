"""
Test Supabase Storage bucket
"""
import os
from supabase import create_client

SUPABASE_URL = "https://ceyynxrnsuggncjmpwhv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzNzE3OH0.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("[*] Testing Supabase Storage...")
try:
    buckets = supabase.storage.list_buckets()
    print(f"[+] Found {len(buckets)} buckets:")
    for bucket in buckets:
        print(f"   - {bucket.name} (public: {bucket.public})")
    
    photos_bucket = [b for b in buckets if b.name == "PHOTOS"]
    if photos_bucket:
        print("\n[+] PHOTOS bucket exists and is configured!")
    else:
        print("\n[-] PHOTOS bucket NOT FOUND!")
        exit(1)
    
except Exception as e:
    print(f"[-] Error listing buckets: {e}")
    exit(1)

print("\n[*] Testing file upload...")
try:
    test_content = b"Test receipt image content"
    test_path = "receipts/test/test_receipt.txt"
    
    result = supabase.storage.from_("PHOTOS").upload(
        path=test_path,
        file=test_content,
        file_options={"content-type": "text/plain", "upsert": "true"}
    )
    
    print(f"[+] File uploaded successfully!")
    
    public_url = supabase.storage.from_("PHOTOS").get_public_url(test_path)
    print(f"[>] Public URL: {public_url}")
    
    supabase.storage.from_("PHOTOS").remove([test_path])
    print("[+] Test file cleaned up")
    
    print("\n" + "="*60)
    print("[SUCCESS] Storage is working perfectly!")
    print("="*60)
    
except Exception as e:
    print(f"[-] Upload failed: {e}")
    print("\n[!] Possible issues:")
    print("   - Check if policies were created correctly")
    print("   - Make sure bucket is public")
    exit(1)
