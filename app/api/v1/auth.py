"""
Authentication API Endpoints for MI Learning Platform

This module provides authentication endpoints using Supabase Auth.
It replaces the previous broken implementation with a robust, secure solution.

Endpoints:
- POST /auth/register - Register a new user
- POST /auth/login - Login existing user
- POST /auth/logout - Logout user
- GET /auth/me - Get current user info
- GET /auth/refresh - Refresh access token
- GET /auth/health - Auth service health check
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from supabase import Client

from app.config import settings
from app.core.supabase import get_supabase, get_supabase_admin
from app.core.auth import (
    get_current_user,
    get_auth_context,
    AuthContext,
    decode_jwt_token,
    AuthenticationError,
)

router = APIRouter()
security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


# =====================================================
# Request/Response Models
# =====================================================


class RegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)


class LoginRequest(BaseModel):
    """User login request"""

    email: EmailStr
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    """User information response"""

    id: str
    email: str
    display_name: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response with tokens"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # 1 hour default
    user: UserResponse


class TokenRefreshResponse(BaseModel):
    """Token refresh response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutResponse(BaseModel):
    """Logout response"""

    message: str


# =====================================================
# Helper Functions
# =====================================================


def create_user_profile(
    user_id: str, email: str, display_name: Optional[str], supabase_admin: Client
):
    """
    Create a user profile in the database.

    Args:
        user_id: The user's UUID from Supabase Auth
        email: User's email
        display_name: User's display name
        supabase_admin: Supabase admin client

    Returns:
        Created profile data
    """
    try:
        # First try to insert into 'users' table if it exists (to satisfy FK constraints)
        try:
            supabase_admin.table("users").insert(
                {
                    "id": user_id,
                    "email": email,
                    # Some schemas put display_name in users table
                    "display_name": display_name,
                    "created_at": "now()",
                }
            ).execute()
            logger.info(f"Created user record in 'users' table for {user_id}")
        except Exception as e:
            # Ignore if table doesn't exist or user already exists, but log it
            logger.info(
                f"Skipping 'users' table insertion (might not exist or already present): {e}"
            )

        response = (
            supabase_admin.table("user_profiles")
            .insert(
                {
                    "user_id": user_id,
                    "display_name": display_name,
                    "total_points": 0,
                    "level": 1,
                    "modules_completed": 0,
                    "change_talk_evoked": 0,
                    "reflections_offered": 0,
                    "technique_mastery": {},
                }
            )
            .execute()
        )

        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error creating user profile: {e}", exc_info=True)
        # Raise exception so we know if profile creation fails
        raise e


# =====================================================
# Endpoints
# =====================================================


@router.get("/health")
async def health_check():
    """Auth service health check"""
    return {"status": "healthy", "service": "authentication", "version": "2.0"}


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(request: RegisterRequest):
    """
    Register a new user.

    Creates a new user account with Supabase Auth and initializes
    their profile in the database.

    Args:
        request: Registration request with email, password, and optional display name

    Returns:
        AuthResponse with access token and user info

    Raises:
        HTTPException: If registration fails (e.g., email already exists)
    """
    logger.info(f"Registration attempt for email: {request.email}")

    try:
        supabase = get_supabase()
        logger.info("Supabase client obtained successfully")
    except Exception as e:
        logger.error(f"Failed to get Supabase client: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {str(e)}",
        )

    try:
        supabase_admin = get_supabase_admin()
        logger.info("Supabase admin client obtained successfully")
    except Exception as e:
        logger.error(f"Failed to get Supabase admin client: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database admin connection error: {str(e)}",
        )

    try:
        # Sign up with Supabase Auth
        logger.info("Attempting to sign up user with Supabase Auth")

        sign_up_data = {
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "display_name": request.display_name or request.email.split("@")[0]
                }
            },
        }

        # Only add redirect if SITE_URL is configured
        if settings.SITE_URL:
            sign_up_data["options"]["email_redirect_to"] = settings.SITE_URL

        auth_response = supabase.auth.sign_up(sign_up_data)

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed: no user created",
            )

        user = auth_response.user

        # Create user profile in database
        # Note: This is also handled by the database trigger, but we do it explicitly
        # to ensure it exists immediately for the subsequent API calls
        display_name = request.display_name or request.email.split("@")[0]
        create_user_profile(str(user.id), request.email, display_name, supabase_admin)

        # Get the session (may be None if email confirmation is required)
        session = auth_response.session

        if session:
            return AuthResponse(
                access_token=session.access_token,
                token_type="bearer",
                expires_in=session.expires_in or 3600,
                user=UserResponse(
                    id=str(user.id), email=user.email, display_name=display_name
                ),
            )
        else:
            # Email confirmation required - return user without token
            # User will need to confirm email then login
            return AuthResponse(
                access_token="",
                token_type="bearer",
                expires_in=0,
                user=UserResponse(
                    id=str(user.id), email=user.email, display_name=display_name
                ),
            )

    except Exception as e:
        error_msg = str(e).lower()

        # Handle specific Supabase auth errors
        if "user already registered" in error_msg or "already exists" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )
        elif "password" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet requirements",
            )
        elif "email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address"
            )
        else:
            logger.error(f"Registration error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {str(e)}",
            )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login an existing user.

    Authenticates the user with Supabase Auth and returns an access token.

    Args:
        request: Login request with email and password

    Returns:
        AuthResponse with access token and user info

    Raises:
        HTTPException: If login fails (invalid credentials)
    """
    logger.info(f"Login attempt for email: {request.email}")

    try:
        supabase = get_supabase()
        logger.info("Supabase client obtained successfully for login")
    except Exception as e:
        logger.error(f"Failed to get Supabase client for login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {str(e)}",
        )

    try:
        # Sign in with Supabase Auth
        logger.info("Attempting to sign in with Supabase Auth")
        auth_response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        user = auth_response.user
        session = auth_response.session

        # Get display name from user metadata
        user_metadata = user.user_metadata or {}
        display_name = user_metadata.get("display_name") or request.email.split("@")[0]

        # Update last_active_at in user profile
        try:
            supabase_admin = get_supabase_admin()
            supabase_admin.table("user_profiles").update(
                {"last_active_at": "now()"}
            ).eq("user_id", str(user.id)).execute()
        except Exception as e:
            logger.warning(f"Failed to update last_active_at: {e}")

        return AuthResponse(
            access_token=session.access_token,
            token_type="bearer",
            expires_in=session.expires_in or 3600,
            user=UserResponse(
                id=str(user.id), email=user.email, display_name=display_name
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        error_str = str(e)

        # Log the full error for debugging
        logger.error(f"Login error for {request.email}: {error_str}")

        # Handle specific Supabase auth errors
        if "invalid login credentials" in error_msg or "invalid password" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        elif "email not confirmed" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not confirmed. Please check your inbox.",
            )
        elif "user not found" in error_msg or "user not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        elif "user is banned" in error_msg or "banned" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account has been disabled. Please contact support.",
            )
        elif "jsondecode" in error_msg or "bad request" in error_msg:
            # This might indicate a configuration issue
            logger.error(f"Supabase auth configuration error: {error_str}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error. Please try again later.",
            )
        else:
            logger.error(f"Unexpected login error: {error_str}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed. Please try again.",
            )


@router.post("/logout", response_model=LogoutResponse)
async def logout(auth_context: AuthContext = Depends(get_current_user)):
    """
    Logout the current user.

    Invalidates the user's session on Supabase Auth.

    Args:
        auth_context: Authentication context from dependency

    Returns:
        LogoutResponse confirming logout
    """
    supabase = get_supabase()

    try:
        # Sign out from Supabase
        supabase.auth.sign_out()

        return LogoutResponse(message="Successfully logged out")

    except Exception as e:
        logger.warning(f"Logout error (may be already logged out): {e}")
        # Still return success - user is effectively logged out
        return LogoutResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
async def get_me(auth_context: AuthContext = Depends(get_current_user)):
    """
    Get current user information.

    Returns the authenticated user's profile information.

    Args:
        auth_context: Authentication context from dependency

    Returns:
        UserResponse with user details
    """
    return UserResponse(
        id=auth_context.user_id,
        email=auth_context.email,
        display_name=auth_context.display_name,
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(authorization: Optional[str] = Header(None)):
    """
    Refresh the access token.

    Uses the current (possibly expired) token to get a new one.
    Note: In Supabase, this typically requires the refresh token which
    should be stored securely on the client side.

    Args:
        authorization: Current access token in Authorization header

    Returns:
        TokenRefreshResponse with new access token

    Raises:
        HTTPException: If token cannot be refreshed
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "")

    try:
        # Try to validate the current token first
        payload = decode_jwt_token(token)

        # If token is still valid, return it
        # In a full implementation, you'd use the refresh token here
        return TokenRefreshResponse(
            access_token=token,
            token_type="bearer",
            expires_in=3600,  # This should come from token claims
        )

    except AuthenticationError:
        # Token is expired - in production, use refresh token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class PasswordResetRequest(BaseModel):
    """Password reset request"""

    email: EmailStr


class UpdatePasswordRequest(BaseModel):
    """Update password request"""

    password: str = Field(..., min_length=6, max_length=100)


class ResetPasswordConfirmRequest(BaseModel):
    """Password reset confirmation request with token"""

    access_token: str
    password: str = Field(..., min_length=6, max_length=100)


@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest):
    """
    Request password reset email.

    Sends a password reset email to the user with a link to reset their password.
    The link will redirect to the app's reset password page.

    Args:
        request: PasswordResetRequest with email address

    Returns:
        Success message (always returns success for security)
    """
    try:
        supabase = get_supabase()

        # Build the redirect URL for password reset
        # Use SITE_URL if set, otherwise construct from request
        site_url = settings.SITE_URL or ""
        if not site_url:
            # Fallback - this should be configured in production
            site_url = "https://mi-learning-platform-production.up.railway.app"
        redirect_url = f"{site_url}/reset-password"

        logger.info(f"Sending password reset email to {request.email} with redirect URL: {redirect_url}")

        # Request password reset from Supabase
        # Note: reset_password_email sends the email with a link
        result = supabase.auth.reset_password_email(
            request.email, options={"redirect_to": redirect_url}
        )

        logger.info(f"Password reset email sent successfully to {request.email}")

        return {
            "success": True,
            "message": "If an account exists with this email, a password reset link has been sent.",
        }

    except Exception as e:
        # Log error prominently for debugging
        logger.error(f"Password reset FAILED for {request.email}: {e}")
        # Still return success message for security (don't reveal if email exists)
        return {
            "success": True,
            "message": "If an account exists with this email, a password reset link has been sent.",
        }


@router.post("/update-password")
async def update_password(
    request: UpdatePasswordRequest,
    auth_context: AuthContext = Depends(get_current_user),
):
    """
    Update user password.

    Updates the password for the currently authenticated user.
    This is used after the user clicks the password reset link.

    Args:
        request: UpdatePasswordRequest with new password
        auth_context: Authentication context from the recovery token

    Returns:
        Success message
    """
    try:
        supabase = get_supabase()

        # Update the user's password using the authenticated session
        result = supabase.auth.update_user({"password": request.password})

        if result.user:
            logger.info(
                f"Password updated successfully for user {auth_context.user_id}"
            )
            return {
                "success": True,
                "message": "Password updated successfully. Please log in with your new password.",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update password",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password. Please try again.",
        )


@router.post("/reset-password-confirm")
async def reset_password_confirm(request: ResetPasswordConfirmRequest):
    """
    Reset password using a recovery token from email link.

    This endpoint is used after the user clicks the password reset email link.
    It validates the token using Supabase and updates the password.

    Args:
        request: ResetPasswordConfirmRequest with access token and new password

    Returns:
        Success message
    """
    try:
        supabase = get_supabase()
        supabase_admin = get_supabase_admin()

        # Validate the token and get user info using Supabase's get_user method
        try:
            user_response = supabase.auth.get_user(request.access_token)
            if not user_response or not user_response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token",
                )
            user_id = str(user_response.user.id)
        except Exception as e:
            logger.error(f"Failed to validate token: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token",
            )

        # Update the user's password using admin API
        result = supabase_admin.auth.admin.update_user_by_id(
            user_id,
            {"password": request.password}
        )

        if result.user:
            logger.info(f"Password reset successfully for user {user_id}")
            return {
                "success": True,
                "message": "Password updated successfully. Please log in with your new password.",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update password",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password. Please try again.",
        )


@router.get("/role")
async def get_user_role(auth_context: AuthContext = Depends(get_current_user)):
    """
    Get the current user's role from the users table.

    Returns the role (e.g. 'user', 'admin', 'moderator') for the authenticated user.
    Uses the admin client to bypass RLS.
    """
    try:
        supabase_admin = get_supabase_admin()
        response = (
            supabase_admin.table("users")
            .select("role")
            .eq("id", auth_context.user_id)
            .maybe_single()
            .execute()
        )
        role = "user"
        if response.data and response.data.get("role"):
            role = response.data["role"]
        return {"role": role}
    except Exception as e:
        logger.error(f"Error fetching user role: {e}")
        return {"role": "user"}


@router.get("/verify")
async def verify_token(auth_context: AuthContext = Depends(get_current_user)):
    """
    Verify that the current token is valid.

    This endpoint can be used by the frontend to check if the
    user's session is still valid on app load.

    Args:
        auth_context: Authentication context from dependency

    Returns:
        Verification result with user info
    """
    return {
        "valid": True,
        "user": {
            "id": auth_context.user_id,
            "email": auth_context.email,
            "display_name": auth_context.display_name,
        },
    }
