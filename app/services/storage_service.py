"""
Storage service for handling receipt images (Base64 approach - no Supabase Storage needed)
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from supabase import Client
import base64


class StorageService:
    """Service for receipt image operations using Base64 encoding"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def upload_receipt_image(
        self, 
        user_id: UUID, 
        file_data: bytes, 
        file_name: str,
        content_type: str = "image/jpeg"
    ) -> dict:
        """
        Convert image to Base64 (no actual storage upload needed)
        
        Returns:
            dict with 'path', 'public_url' (as data URL), and 'base64_data'
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_path = f"receipts/{user_id}/{timestamp}_{file_name}"
        
        try:
            # Convert to base64
            base64_data = base64.b64encode(file_data).decode('utf-8')
            
            # Create data URL for OpenAI Vision API
            data_url = f"data:{content_type};base64,{base64_data}"
            
            return {
                "path": file_path,
                "public_url": data_url,  # Use data URL instead of storage URL
                "base64_data": base64_data,
                "content_type": content_type
            }
            
        except Exception as e:
            print(f"Error processing receipt image: {e}")
            raise Exception(f"Failed to process receipt image: {str(e)}")
    
    def delete_receipt_image(self, file_path: str) -> bool:
        """Delete receipt image (no-op since we don't use storage)"""
        # No actual storage to delete from
        return True
    
    def get_receipt_url(self, file_path: str) -> str:
        """Get public URL for receipt image (returns placeholder)"""
        # Since we're using data URLs, there's no persistent URL
        return f"data:image/jpeg;base64,..."
