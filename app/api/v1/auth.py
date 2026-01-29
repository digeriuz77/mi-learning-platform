"""
Authentication API endpoints - Simplified for Supabase

Working Supabase auth using standard Python supabase client.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from app.core.supabase import get_supabase, get_supabase_admin
from app.models.auth import UserRegister, UserLogin, TokenResponse, UserResponse

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
    """Get authenticated user from JWT token."""
    if not credentials or not credentials.credentials:
        return None

    try:
        response = supabase.auth.get_user(credentials.credentials)
        if response and response.user:
            return response.user
    except Exception as e:
        logger.warning(f"Auth check failed: {e}")

    return None


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
) -> dict:
    """Require authentication - raises 401 if not authenticated."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        response = supabase.auth.get_user(credentials.credentials)
        if response and response.user:
            return response.user
    except Exception as e:
        logger.warning(f"Auth failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token"
    )


async def ensure_user_profile(user_id: str, email: str, display_name: str) -> Optional[dict]:
    """Create user profile if it doesn't exist."""
    try:
        supabase_admin = get_supabase_admin()

        # Check if exists
        response = supabase_admin.table('user_profiles').select('*').eq('user_id', user_id).execute()
        if response.data:
            return response.data[0]

        # Create new profile
        result = supabase_admin.table('user_profiles').insert({
            'user_id': user_id,
            'display_name': display_name,
            'total_points': 0,
            'level': 1,
            'modules_completed': 0,
            'change_talk_evoked': 0
        }).execute()

        return result.data[0] if result.data else None
    except Exception as e:
        logger.warning(f"Profile creation failed (table may not exist yet): {e}")
        # Return a fake profile so auth still works
        return {
            'user_id': user_id,
            'display_name': display_name,
            'total_points': 0,
            'level': 1,
            'modules_completed': 0,
            'change_talk_evoked': 0
        }


# =====================================================
# Endpoints
# =====================================================

@router.get("/health")
async def health_check():
    """Auth health check"""
    return {"status": "healthy", "service": "auth"}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, supabase: Client = Depends(get_supabase)):
    """Register new user with Supabase Auth"""
    try:
        logger.info(f"Registration attempt: {user_data.email}")

        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "display_name": user_data.display_name or user_data.email.split('@')[0]
                }
            }
        })

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user. Email may already exist."
            )

        user = auth_response.user
        display_name = user_data.display_name or user.email.split('@')[0]

        # Create profile (non-blocking - won't fail if table doesn't exist)
        try:
            await ensure_user_profile(str(user.id), user.email, display_name)
        except Exception as profile_err:
            logger.warning(f"Profile creation skipped: {profile_err}")

        # Get access token
        if auth_response.session and auth_response.session.access_token:
            access_token = auth_response.session.access_token
        else:
            # Sign in to get token
            signin = supabase.auth.sign_in_with_password({
                "email": user_data.email,
                "password": user_data.password
            })
            access_token = signin.session.access_token

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
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, supabase: Client = Depends(get_supabase)):
    """Login with email and password"""
    try:
        logger.info(f"Login attempt: {user_data.email}")

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
        display_name = user.user_metadata.get('display_name') or user.email.split('@')[0]

        # Ensure profile exists
        await ensure_user_profile(str(user.id), user.email, display_name)

        return TokenResponse(
            access_token=auth_response.session.access_token,
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
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


@router.post("/logout")
async def logout(supabase: Client = Depends(get_supabase)):
    """Logout current user"""
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(require_auth)):
    """Get current user info"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.user_metadata.get('display_name') or current_user.email.split('@')[0],
        created_at=current_user.created_at or datetime.now()
    )
