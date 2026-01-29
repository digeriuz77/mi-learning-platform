"""
Authentication API endpoints

Handles user registration, login, logout, and profile management.
Following the supabase-hello-world pattern for proper auth integration.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from app.core.supabase import get_supabase, get_supabase_admin, test_connection
from app.models.auth import UserRegister, UserLogin, TokenResponse, UserResponse, UserProfile
from app.config import settings

router = APIRouter()
security = HTTPBearer()

logger = logging.getLogger(__name__)


# =====================================================
# Health & Test Endpoints
# =====================================================

@router.get("/test-supabase")
async def test_supabase_connection():
    """Test Supabase connection - hello world style"""
    return await test_connection()


@router.get("/health")
async def auth_health():
    """Health check for auth endpoints"""
    try:
        client = get_supabase()
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


# =====================================================
# Helper Functions
# =====================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
) -> Dict[str, Any]:
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
        # Use get_user to validate and retrieve user
        response = supabase.auth.get_user(token)

        if not response or not response.user:
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


async def get_or_create_user_profile(
    user_id: str,
    email: str,
    supabase_admin: Client
) -> Dict[str, Any]:
    """
    Get or create user profile in app_user table.

    Args:
        user_id: User UUID from Supabase Auth
        email: User email
        supabase_admin: Admin client for bypassing RLS

    Returns:
        dict: User profile data
    """
    try:
        # Try to get existing profile
        response = supabase_admin.table('app_user').select('*').eq('id', user_id).execute()

        if response.data:
            logger.info(f"Found existing profile for user {user_id}")
            return response.data[0]

        # Create new profile if not exists
        # Extract username from email
        username = email.split('@')[0]
        # Make unique by adding random suffix if needed
        existing = supabase_admin.table('app_user').select('id').eq('username', username).execute()
        if existing.data:
            username = f"{username}_{user_id[:8]}"

        new_profile = {
            "id": user_id,
            "username": username,
            "first_name": None,
            "last_name": None
        }

        insert_response = supabase_admin.table('app_user').insert(new_profile).execute()
        logger.info(f"Created new profile for user {user_id}")

        return insert_response.data[0]

    except Exception as e:
        logger.error(f"Error getting/creating user profile: {e}")
        # Return minimal profile so auth doesn't fail
        return {"id": user_id, "username": email.split('@')[0]}


# =====================================================
# Auth Endpoints
# =====================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Register a new user.

    Creates a user in Supabase Auth and creates a user profile.

    Flow:
    1. Sign up user via Supabase Auth
    2. Get or create profile in app_user table
    3. Return access token and user info
    """
    try:
        logger.info(f"Registration attempt for email: {user_data.email}")

        # Get Supabase client
        supabase = get_supabase()
        supabase_admin = get_supabase_admin()

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

        # Check if user was created
        if not auth_response.user:
            logger.error("No user returned from Supabase auth")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user. Email may already be registered."
            )

        user = auth_response.user
        logger.info(f"User created in auth: {user.id}")

        # Get session token
        session = auth_response.session
        access_token = session.access_token if session else None

        if not access_token:
            logger.info("No session token returned, attempting sign in")
            # If no session (email confirmation might be required), try to sign in
            signin_response = supabase.auth.sign_in_with_password({
                "email": user_data.email,
                "password": user_data.password
            })
            access_token = signin_response.session.access_token

        # Create user profile
        profile = await get_or_create_user_profile(str(user.id), user_data.email, supabase_admin)

        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                display_name=profile.get('username', user.email.split('@')[0]),
                created_at=user.created_at or datetime.now()
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "Registration failed. Please try again."
        )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """
    Login with email and password.

    Uses Supabase Auth for authentication.
    """
    try:
        logger.info(f"Login attempt for email: {user_data.email}")

        # Get Supabase client
        supabase = get_supabase()
        supabase_admin = get_supabase_admin()

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

        # Get or ensure user profile exists
        profile = await get_or_create_user_profile(str(user.id), user_data.email, supabase_admin)

        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                display_name=profile.get('username', user.email.split('@')[0]),
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
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout the current user.

    Note: Client should discard the token. This endpoint logs out on the server side.
    """
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
        logger.info(f"User logged out: {current_user.get('id')}")
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current user's profile.
    """
    try:
        supabase_admin = get_supabase_admin()
        user_id = str(current_user.get('id'))

        response = supabase_admin.table('app_user').select('*').eq('id', user_id).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )

        profile = response.data[0]
        return UserProfile(
            id=str(profile['id']),
            username=profile.get('username', ''),
            email=current_user.get('email', ''),
            first_name=profile.get('first_name'),
            last_name=profile.get('last_name'),
            created_at=profile.get('created_at', datetime.now())
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch profile"
        )


@router.put("/me", response_model=UserProfile)
async def update_profile(
    display_name: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the current user's profile.
    """
    try:
        supabase_admin = get_supabase_admin()
        user_id = str(current_user.get('id'))

        update_data = {}
        if display_name is not None:
            update_data['username'] = display_name
        if first_name is not None:
            update_data['first_name'] = first_name
        if last_name is not None:
            update_data['last_name'] = last_name

        if not update_data:
            # No updates, return current profile
            return await get_current_user_profile(current_user)

        response = supabase_admin.table('app_user').update(update_data).eq('id', user_id).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )

        profile = response.data[0]
        return UserProfile(
            id=str(profile['id']),
            username=profile.get('username', ''),
            email=current_user.get('email', ''),
            first_name=profile.get('first_name'),
            last_name=profile.get('last_name'),
            created_at=profile.get('created_at', datetime.now())
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )
