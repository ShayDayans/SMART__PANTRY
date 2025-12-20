"""
Supabase client configuration
"""
from supabase import create_client, Client
from app.core.config import settings
from typing import Optional


class SupabaseClient:
    """Singleton Supabase client"""
    _client: Optional[Client] = None
    _admin_client: Optional[Client] = None
    
    @classmethod
    def get_client(cls, use_admin: bool = False) -> Client:
        """
        Get Supabase client instance
        Args:
            use_admin: If True, use service_role_key (bypasses RLS). If False, use anon_key (respects RLS)
        """
        if use_admin:
            if cls._admin_client is None:
                if not settings.supabase_url or not settings.supabase_service_role_key:
                    raise ValueError("Supabase URL and service_role_key must be set for admin client")
                cls._admin_client = create_client(
                    settings.supabase_url,
                    settings.supabase_service_role_key
                )
            return cls._admin_client
        else:
            if cls._client is None:
                if not settings.supabase_url or not settings.supabase_anon_key:
                    raise ValueError(
                        "Supabase URL and anon_key must be set. "
                        "Please create a .env file with SUPABASE_URL and SUPABASE_ANON_KEY"
                    )
                cls._client = create_client(
                    settings.supabase_url,
                    settings.supabase_anon_key
                )
            return cls._client


def get_supabase(use_admin: bool = False) -> Client:
    """
    Dependency function for FastAPI routes
    Returns Supabase client instance
    """
    return SupabaseClient.get_client(use_admin=use_admin)

