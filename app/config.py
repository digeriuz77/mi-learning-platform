"""
Application Configuration using Pydantic Settings
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List, Union


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required environment variables (Supabase):
        - SUPABASE_URL
        - SUPABASE_KEY
        - SUPABASE_SERVICE_ROLE_KEY
        - SUPABASE_JWT_SECRET

    All other settings have sensible defaults.
    """

    # Supabase Configuration (Required)
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # Application Settings (Optional - have defaults)
    APP_NAME: str = "MI Learning Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # CORS Settings - default allows all origins for easy deployment
    # Set to specific origins in production if needed
    CORS_ORIGINS: List[str] = ["*"]

    # JWT Settings
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list"""
        if v is None or v == "":
            return ["*"]
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
