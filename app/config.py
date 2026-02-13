"""
Application Configuration using Pydantic Settings
"""

from pydantic import field_validator, ValidationError
from pydantic_settings import BaseSettings
from typing import List
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env.local only if Railway env vars aren't set
if not os.getenv("SUPABASE_URL"):
    load_dotenv(".env.local")


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required environment variables (Supabase):
        - SUPABASE_URL
        - SUPABASE_KEY
        - SUPABASE_SERVICE_ROLE_KEY
        - SUPABASE_JWT_SECRET

    Optional environment variables (Chat Practice):
        - OPENAI_API_KEY: API key for OpenAI (required for chat practice feature)
        - OPENAI_MODEL: Model to use (default: gpt-realtime-mini-2025-12-15)

    All other settings have sensible defaults.
    """

    # Supabase Configuration (Required)
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # Server Settings
    PORT: int = 8000

    # Application Settings (Optional - have defaults)
    APP_NAME: str = "MI Learning Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Deployment URL (for auth redirects)
    # IMPORTANT: Set this to your production URL for email redirects to work
    SITE_URL: str = ""

    # CORS Settings - SECURITY: Do not use ["*"] with allow_credentials=True
    # Set CORS_ORIGINS env var to comma-separated allowed origins in production
    CORS_ORIGINS: List[str] = []

    # JWT Settings
    JWT_ALGORITHM: str = "HS256"
    # Note: Token expiry is controlled by Supabase Auth, not this application.

    @field_validator("SUPABASE_URL", mode="before")
    @classmethod
    def validate_supabase_url(cls, v):
        """Validate Supabase URL format"""
        if not v:
            raise ValueError("SUPABASE_URL is required")
        if not v.startswith("http"):
            raise ValueError("SUPABASE_URL must start with http:// or https://")
        return v.rstrip("/")  # Remove trailing slash

    # SECURITY: OpenAI API key should be accessed through Settings, not os.getenv()
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-mini"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list.
        
        SECURITY: Defaults to empty list (no CORS) rather than ["*"] to prevent
        credential leakage via cross-origin requests.
        """
        if v is None or v == "":
            return []
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = [".env", ".env.local"]
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from old env files


# Try to load settings and provide helpful error messages
try:
    settings = Settings()
except ValidationError as e:
    print("=" * 60)
    print("CONFIGURATION ERROR")
    print("=" * 60)
    print("Failed to load required environment variables.")
    print()
    print("Required variables:")
    print("  - SUPABASE_URL: Your Supabase project URL")
    print("  - SUPABASE_KEY: Your Supabase anon/public key")
    print("  - SUPABASE_SERVICE_ROLE_KEY: Your Supabase service role key")
    print("  - SUPABASE_JWT_SECRET: Your Supabase JWT secret")
    print()
    print("For Railway deployment, set these in your environment variables.")
    print("See .env.example for the complete list of required variables.")
    print()
    print("Error details:")
    for error in e.errors():
        field = error.get("loc", ["unknown"])[0]
        msg = error.get("msg", "unknown error")
        print(f"  - {field}: {msg}")
    print("=" * 60)
    sys.exit(1)
except Exception as e:
    print("=" * 60)
    print("UNEXPECTED CONFIGURATION ERROR")
    print("=" * 60)
    print(f"Error loading configuration: {e}")
    print("Please check your environment variables and try again.")
    print("=" * 60)
    sys.exit(1)
