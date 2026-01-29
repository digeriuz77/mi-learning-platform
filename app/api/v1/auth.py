"""
Simplified Authentication API endpoints

Uses Supabase Auth directly without additional profile tables.
This is the simplest approach - just let Supabase handle all auth.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from app.core.supabase import get_supabase
from app.models.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from app.config import settings

router = APIRouter()
security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


# =====================================================
# Helper Functions
# =====================================================

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase: Client = Depends(get_supabase)
) -> Optional[dict]:
    """
    Get the current authenticated user from JWT token.

    Returns None if not authenticated (for optional auth).
    """
    try:
        if not credentials:
            return None

        token = credentials.credentials
        if not token:
            return None

        response = supabase.auth.get_user(token)

        if response and response.user:
            logger.info(f"Authenticated user: {response.user.email}")
            return response.user

        return None
    except Exception as e:
        logger.warning(f"Auth check failed: {e}")
        return None


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
) -> dict:
    """
    Require authentication - raises 401 if not authenticated.
    """
    user = get_current_user(credentials, supabase)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return user


# =====================================================
# Health & Test Endpoints
# =====================================================

@router.get("/test-supabase")
async def test_supabase_connection(supabase: Client = Depends(get_supabase)):
    """Test Supabase connection - hello world style"""
    try:
        # Test basic connection
        response = supabase.table('learning_modules').select('count').execute()

        return {
            "status": "success",
            "supabase_url": settings.SUPABASE_URL[:30] + "...",
            "modules_count": len(response.data) if response.data else 0,
            "config_present": {
                "supabase_key": bool(settings.SUPABASE_KEY),
                "service_key": bool(settings.SUPABASE_SERVICE_ROLE_KEY),
                "jwt_secret": bool(settings.SUPABASE_JWT_SECRET)
            },
            "message": "✓ Supabase connection working!"
        }
    except Exception as e:
        logger.error(f"Supabase test error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "supabase_url": settings.SUPABASE_URL[:30] + "..." if settings.SUPABASE_URL else "None"
        }


@router.get("/health")
async def auth_health(supabase: Client = Depends(get_supabase)):
    """Health check for auth endpoints"""
    try:
        return {
            "status": "healthy",
            "service": "auth",
            "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)
        }
    except Exception as e:
        logger.error(f"Auth health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@router.get("/me")
async def get_current_user_profile(current_user: dict = Depends(require_auth)):
    """Get the current user's profile from Supabase Auth"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.user_metadata.get('display_name') or current_user.email.split('@')[0],
        created_at=current_user.created_at or datetime.now()
    )


# =====================================================
# Auth Endpoints
# =====================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, supabase: Client = Depends(get_supabase)):
    """
    Register a new user using Supabase Auth.

    This is a simplified version that only uses Supabase Auth
    without any additional profile tables.
    """
    try:
        logger.info(f"Registration attempt for email: {user_data.email}")

        # Register with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "display_name": user_data.display_name or user_data.email.split('@')[0]
                }
            }
        })

        logger.info(f"Supabase auth response received")

        if not auth_response.user:
            logger.error("No user returned from Supabase auth")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user. Email may already be registered."
            )

        user = auth_response.user
        logger.info(f"User created: {user.id}")

        # Get session token
        session = auth_response.session
        access_token = session.access_token if session else None

        if not access_token:
            logger.info("No session token returned, attempting sign in")
            # If no session, try to sign in
            signin_response = supabase.auth.sign_in_with_password({
                "email": user_data.email,
                "password": user_data.password
            })
            access_token = signin_response.session.access_token
            logger.info(f"Sign in successful, token: {access_token[:20]}..." if access_token else "No token from sign in")

        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                display_name=user_data.display_name or user.email.split('@')[0],
                created_at=user.created_at or datetime.now()
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, supabase: Client = Depends(get_supabase)):
    """
    Login with email and password using Supabase Auth.
    """
    try:
        logger.info(f"Login attempt for email: {user_data.email}")

        # Sign in with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        user = auth_response.user
        access_token = auth_response.session.access_token

        logger.info(f"User logged in: {user.id}")

        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                display_name=user.user_metadata.get('display_name') or user.email.split('@')[0],
                created_at=user.created_at or datetime.now()
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(require_auth), supabase: Client = Depends(get_supabase)):
    """
    Logout the current user.
    """
    try:
        supabase.auth.sign_out()
        logger.info(f"User logged out: {current_user.get('id')}")
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed"
        )
