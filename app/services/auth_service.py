"""
Authentication service using custom users table
"""
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from supabase import Client
from app.schemas.auth import UserCreate, UserResponse
from app.core.security import get_password_hash, verify_password, create_access_token
from fastapi import HTTPException, status
import re


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string from Supabase (handles various formats)"""
    # Remove timezone info and normalize
    dt_str = dt_str.replace("Z", "+00:00")
    
    # Try to parse with fromisoformat first
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # If that fails, try to fix microsecond precision
        # Match pattern like: 2025-12-22T17:28:45.1944+00:00
        pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)([+-]\d{2}:\d{2})'
        match = re.match(pattern, dt_str)
        if match:
            base_time = match.group(1)
            microseconds = match.group(2)
            timezone = match.group(3)
            # Limit microseconds to 6 digits
            microseconds = microseconds[:6].ljust(6, '0')
            dt_str = f"{base_time}.{microseconds}{timezone}"
            return datetime.fromisoformat(dt_str)
        
        # Last resort: try parsing without microseconds
        try:
            dt_str_no_micro = re.sub(r'\.\d+', '', dt_str)
            return datetime.fromisoformat(dt_str_no_micro)
        except ValueError:
            # If all else fails, return current time
            return datetime.utcnow()


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user"""
        # Check if user already exists
        existing = self.supabase.table("users").select("user_id").eq("email", user_data.email.lower()).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user_id = uuid4()
        hashed_password = get_password_hash(user_data.password)
        
        user_record = {
            "user_id": str(user_id),
            "email": user_data.email.lower(),
            "hashed_password": hashed_password,
            "username": user_data.username,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table("users").insert(user_record).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        user = result.data[0]
        return UserResponse(
            user_id=UUID(user["user_id"]),
            email=user["email"],
            username=user.get("username"),
            created_at=parse_datetime(user["created_at"]),
            updated_at=parse_datetime(user["updated_at"])
        )
    
    def authenticate_user(self, email: str, password: str) -> Optional[UserResponse]:
        """Authenticate a user and return user data if valid"""
        # Get user by email
        result = self.supabase.table("users").select("*").eq("email", email.lower()).execute()
        
        if not result.data:
            return None
        
        user = result.data[0]
        
        # Verify password
        if not verify_password(password, user["hashed_password"]):
            return None
        
        return UserResponse(
            user_id=UUID(user["user_id"]),
            email=user["email"],
            username=user.get("username"),
            created_at=parse_datetime(user["created_at"]),
            updated_at=parse_datetime(user["updated_at"])
        )
    
    def get_user_by_id(self, user_id: UUID) -> Optional[UserResponse]:
        """Get user by ID"""
        result = self.supabase.table("users").select("*").eq("user_id", str(user_id)).execute()
        
        if not result.data:
            return None
        
        user = result.data[0]
        return UserResponse(
            user_id=UUID(user["user_id"]),
            email=user["email"],
            username=user.get("username"),
            created_at=parse_datetime(user["created_at"]),
            updated_at=parse_datetime(user["updated_at"])
        )
    
    def login(self, email: str, password: str) -> dict:
        """Login user and return token"""
        user = self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user.user_id), "email": user.email})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }

    