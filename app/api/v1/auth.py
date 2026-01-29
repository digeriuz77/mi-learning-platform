"""
Authentication API endpoints

Handles user registration, login, logout, and profile management.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from datetime import datetime, timedelta
from typing import Optional

from app.core.supabase import get_supabase
from app.models.auth import UserRegister, UserLogin, TokenResponse, UserResponse, UserProfile
from app.config import settings

router = APIRouter()
security = HTTPBearer()

# Set up logging
logger = logging.getLogger(__name__)


@router.get("/test-supabase")
async def test_supabase(supabase: Client = Depends(get_supabase)):
    """Test Supabase connection"""
    try:
        # Test basic connection
        response = supabase.table('app_user').select('count').execute()
        return {
            "status": "success",
            "supabase_url": settings.SUPABASE_URL[:30] + "...",
            "user_profiles_count": response.data,
            "keys_present": {
                "supabase_key": bool(settings.SUPABASE_KEY),
                "service_key": bool(settings.SUPABASE_SERVICE_ROLE_KEY),
                "jwt_secret": bool(settings.SUPABASE_JWT_SECRET)
            }
        }
    except Exception as e:
        logger.error(f"Supabase test error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "supabase_url": settings.SUPABASE_URL[:30] + "..." if settings.SUPABASE_URL else "None"
        }

# =====================================================
# Helper Functions
# =====================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
) -> dict:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        supabase: Supabase client

    Returns:
        dict: User data

    Raises:
        HTTPException: If token is invalid
    """
    try:
        token = credentials.credentials
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return response.user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_user_profile(
    user_id: str,
    supabase: Client = Depends(get_supabase)
) -> Optional[dict]:
    """
    Get user profile by user ID.

    Args:
        user_id: User UUID
        supabase: Supabase client

    Returns:
        dict: User profile or None
    """
    response = supabase.table('app_user').select('*').eq('id', user_id).execute()
    if response.data:
        return response.data[0]
    return None


# =====================================================
# Endpoints
# =====================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    supabase: Client = Depends(get_supabase)
):
    """
    Register a new user.

    Creates a user in Supabase Auth and creates a user profile.
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
        
        logger.info(f"Supabase auth response: {auth_response}")

        if not auth_response.user:
            logger.error("No user returned from Supabase auth")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )

        user = auth_response.user
        logger.info(f"User created: {user.id}")

        # Get session token
        session = auth_response.session
        access_token = session.access_token if session else None

        if not access_token:
            logger.info("No session token, attempting sign in")
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
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    supabase: Client = Depends(get_supabase)
):
    """
    Login with email and password.
    """
    try:
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

        # Update last_active_at
        profile = await get_user_profile(str(user.id), supabase)
        if profile:
            supabase.table('user_profiles').update({
                'last_active_at': datetime.now().isoformat()
            }).eq('user_id', str(user.id)).execute()

        display_name = profile.get('display_name') if profile else user.email.split('@')[0]

        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                display_name=display_name,
                created_at=user.created_at or datetime.now()
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Logout the current user.
    """
    try:
        supabase.auth.sign_out()
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get the current user's profile with stats.
    """
    profile = await get_user_profile(str(current_user.id), supabase)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile


@router.put("/me", response_model=UserProfile)
async def update_profile(
    display_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Update the current user's profile.
    """
    update_data = {}
    if display_name is not None:
        update_data['display_name'] = display_name

    if not update_data:
        profile = await get_user_profile(str(current_user.id), supabase)
        return profile

    response = supabase.table('user_profiles').update(update_data).eq('user_id', str(current_user.id)).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return response.data[0]
