"""
Application Configuration using Pydantic Settings
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Optional, Union


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # Application Settings
    APP_NAME: str = "MI Learning Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # CORS Settings - accepts comma-separated string or list
    CORS_ORIGINS: Union[str, list[str]] = "http://localhost:8000,http://localhost:3000"

    # JWT Settings
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list"""
        if isinstance(v, str):
            # Handle empty string
            if not v.strip():
                return ["http://localhost:8000"]
            # Split comma-separated string into list
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
