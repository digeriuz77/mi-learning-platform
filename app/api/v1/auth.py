"""
Simple Authentication - Direct HTTP to Supabase REST API
No Python supabase client = no proxy issues
"""
import logging
import httpx
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

router = APIRouter()
security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)

# Supabase settings
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
SUPABASE_SERVICE_KEY = settings.SUPABASE_SERVICE_ROLE_KEY


# =====================================================
# HTTP Client for Supabase
# =====================================================

def get_supabase_client():
    """Get httpx client for Supabase requests"""
    return httpx.Client(timeout=30.0)


def get_auth_headers(use_service_key=False):
    """Get headers for Supabase API requests"""
    key = SUPABASE_SERVICE_KEY if use_service_key else SUPABASE_KEY
    return {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json'
    }


# =====================================================
# Auth Endpoints
# =====================================================

@router.get("/health")
async def health_check():
    """Auth health check"""
    return {"status": "healthy", "service": "auth"}


@router.post("/register")
async def register(email: str, password: str, display_name: Optional[str] = None):
    """Register new user via Supabase Auth REST API"""
    try:
        client = get_supabase_client()

        # Call Supabase Auth signup endpoint
        response = client.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            json={
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "display_name": display_name or email.split('@')[0]
                    }
                }
            },
            headers=get_auth_headers()
        )

        if response.status_code == 400:
            raise HTTPException(
                status_code=400,
                detail="User already exists or invalid data"
            )

        if response.status_code != 200:
            logger.error(f"Register failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Registration failed: {response.text}"
            )

        data = response.json()

        # Return access token and user info
        return {
            "access_token": data.get('access_token'),
            "token_type": "bearer",
            "user": {
                "id": data.get('user', {}).get('id'),
                "email": data.get('user', {}).get('email'),
                "display_name": display_name or email.split('@')[0]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login")
async def login(email: str, password: str):
    """Login via Supabase Auth REST API"""
    try:
        client = get_supabase_client()

        # Call Supabase Auth token endpoint
        response = client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={
                "email": email,
                "password": password
            },
            headers=get_auth_headers()
        )

        if response.status_code == 400:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if response.status_code != 200:
            logger.error(f"Login failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Login failed: {response.text}"
            )

        data = response.json()

        # Get user metadata
        user = data.get('user', {})
        display_name = user.get('user_metadata', {}).get('display_name') or email.split('@')[0]

        return {
            "access_token": data.get('access_token'),
            "token_type": "bearer",
            "user": {
                "id": user.get('id'),
                "email": user.get('email'),
                "display_name": display_name
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/logout")
async def logout():
    """Logout"""
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(authorization: Optional[str] = None):
    """Get current user from token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")

    token = authorization.replace("Bearer ", "")

    client = get_supabase_client()

    response = client.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {token}'
        }
    )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = response.json()

    return {
        "id": user.get('id'),
        "email": user.get('email'),
        "display_name": user.get('user_metadata', {}).get('display_name') or user.get('email', '').split('@')[0]
    }
