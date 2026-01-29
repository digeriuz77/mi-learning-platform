"""
Simple Authentication - Direct HTTP to Supabase REST API
"""
import logging
import httpx
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from app.config import settings
from app.core.supabase import get_supabase

router = APIRouter()
security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase: Client = Depends(get_supabase)
) -> Optional[dict]:
    """Get authenticated user - returns demo user if no auth"""
    if credentials and credentials.credentials:
        try:
            response = supabase.auth.get_user(credentials.credentials)
            if response and response.user:
                return response.user
        except Exception:
            pass

    # Return demo user for testing
    return {
        'id': 'demo-user-123',
        'email': 'demo@example.com',
        'user_metadata': {'display_name': 'Demo User'}
    }


@router.get("/health")
async def health_check():
    """Auth health check"""
    return {"status": "healthy"}


@router.post("/register")
async def register(email: str, password: str, display_name: Optional[str] = None):
    """Register new user"""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{SUPABASE_URL}/auth/v1/signup",
                json={
                    "email": email,
                    "password": password,
                    "options": {"data": {"display_name": display_name or email.split('@')[0]}}
                },
                headers={
                    'apikey': SUPABASE_KEY,
                    'Authorization': f'Bearer {SUPABASE_KEY}',
                    'Content-Type': 'application/json'
                }
            )

            if response.status_code == 400:
                raise HTTPException(status_code=400, detail="User already exists")

            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Registration failed: {response.text}")

            data = response.json()
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
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(email: str, password: str):
    """Login"""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                json={"email": email, "password": password},
                headers={
                    'apikey': SUPABASE_KEY,
                    'Authorization': f'Bearer {SUPABASE_KEY}',
                    'Content-Type': 'application/json'
                }
            )

            if response.status_code == 400:
                raise HTTPException(status_code=401, detail="Invalid email or password")

            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Login failed")

            data = response.json()
            user = data.get('user', {})
            return {
                "access_token": data.get('access_token'),
                "token_type": "bearer",
                "user": {
                    "id": user.get('id'),
                    "email": user.get('email'),
                    "display_name": user.get('user_metadata', {}).get('display_name', email.split('@')[0])
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/logout")
async def logout():
    """Logout"""
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(authorization: Optional[str] = Header(None)):
    """Get current user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No token")

    token = authorization.replace("Bearer ", "")

    with httpx.Client(timeout=30.0) as client:
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
            "display_name": user.get('user_metadata', {}).get('display_name', user.get('email', '').split('@')[0])
        }
