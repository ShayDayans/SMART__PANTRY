"""
Authentication API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.db.supabase_client import get_supabase
from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate, UserLogin, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(supabase: Client = Depends(get_supabase)) -> AuthService:
    """Dependency to get auth service"""
    return AuthService(supabase)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    service: AuthService = Depends(get_auth_service)
):
    """Register a new user"""
    try:
        user = service.create_user(user_data)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )


@router.post("/login", response_model=UserResponse)
def login(
    credentials: UserLogin,
    service: AuthService = Depends(get_auth_service)
):
    """Login user - verify credentials and return user info"""
    try:
        user = service.authenticate_user(credentials.email, credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to login: {str(e)}"
        )

