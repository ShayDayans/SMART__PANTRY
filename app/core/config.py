"""
Application configuration for Supabase API
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List

# Get project root directory (where run.py is located)
# This file is in app/core/, so we go up 2 levels to get to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings for Supabase API backend"""
    
    # Supabase API (required for API-only approach)
    supabase_url: str = "https://ceyynxrnsuggncjmpwhv.supabase.co"
    supabase_anon_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzNzE3OH0.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k"  # Public anon key (respects RLS)
    supabase_service_role_key: Optional[str] = None  # Service role key (bypasses RLS) - use carefully!
    
    # OpenAI for receipt scanning
    openai_api_key: Optional[str] = None
    
    # API
    api_title: str = "Smart Pantry API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    
    # CORS
    cors_origins: List[str] = ["*"]
    
    class Config:
        env_file = str(ENV_FILE_PATH)
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

