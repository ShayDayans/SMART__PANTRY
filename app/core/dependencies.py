"""
Dependencies for authentication
"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from supabase import Client
from app.db.supabase_client import get_supabase
from app.services.auth_service import AuthService
from app.schemas.auth import UserResponse
import base64

security = HTTPBasic()


async def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
) -> UserResponse:
    """Get current authenticated user from Basic Auth (email and password)"""
    email = credentials.username
    password = credentials.password
    
    # Authenticate user with email and password
    auth_service = AuthService(supabase)
    user = auth_service.authenticate_user(email, password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return user


def get_current_user_id(
    current_user: UserResponse = Depends(get_current_user)
) -> UUID:
    """Get current user ID from authenticated user"""
    return current_user.user_id

