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
    AuthenticationError
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

def create_user_profile(user_id: str, display_name: Optional[str], supabase_admin: Client):
    """
    Create a user profile in the database.
    
    Args:
        user_id: The user's UUID from Supabase Auth
        display_name: User's display name
        supabase_admin: Supabase admin client
        
    Returns:
        Created profile data
    """
    try:
        response = supabase_admin.table('user_profiles').insert({
            'user_id': user_id,
            'display_name': display_name,
            'total_points': 0,
            'level': 1,
            'modules_completed': 0,
            'change_talk_evoked': 0,
            'reflections_offered': 0,
            'technique_mastery': {}
        }).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error creating user profile: {e}")
        # Don't raise - profile creation failure shouldn't break registration
        return None


# =====================================================
# Endpoints
# =====================================================

@router.get("/health")
async def health_check():
    """Auth service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "2.0"
    }


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
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
            detail=f"Database connection error: {str(e)}"
        )
    
    try:
        supabase_admin = get_supabase_admin()
        logger.info("Supabase admin client obtained successfully")
    except Exception as e:
        logger.error(f"Failed to get Supabase admin client: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database admin connection error: {str(e)}"
        )
    
    try:
        # Sign up with Supabase Auth
        logger.info("Attempting to sign up user with Supabase Auth")
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "display_name": request.display_name or request.email.split('@')[0]
                },
                "email_redirect_to": settings.SITE_URL
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed: no user created"
            )
        
        user = auth_response.user
        
        # Create user profile in database
        # Note: This is also handled by the database trigger, but we do it explicitly
        # to ensure it exists immediately for the subsequent API calls
        display_name = request.display_name or request.email.split('@')[0]
        create_user_profile(str(user.id), display_name, supabase_admin)
        
        # Get the session (may be None if email confirmation is required)
        session = auth_response.session
        
        if session:
            return AuthResponse(
                access_token=session.access_token,
                token_type="bearer",
                expires_in=session.expires_in or 3600,
                user=UserResponse(
                    id=str(user.id),
                    email=user.email,
                    display_name=display_name
                )
            )
        else:
            # Email confirmation required - return user without token
            # User will need to confirm email then login
            return AuthResponse(
                access_token="",
                token_type="bearer",
                expires_in=0,
                user=UserResponse(
                    id=str(user.id),
                    email=user.email,
                    display_name=display_name
                )
            )
            
    except Exception as e:
        error_msg = str(e).lower()
        
        # Handle specific Supabase auth errors
        if "user already registered" in error_msg or "already exists" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        elif "password" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet requirements"
            )
        elif "email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email address"
            )
        else:
            logger.error(f"Registration error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {str(e)}"
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
            detail=f"Database connection error: {str(e)}"
        )
    
    try:
        # Sign in with Supabase Auth
        logger.info("Attempting to sign in with Supabase Auth")
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = auth_response.user
        session = auth_response.session
        
        # Get display name from user metadata
        user_metadata = user.user_metadata or {}
        display_name = user_metadata.get("display_name") or request.email.split('@')[0]
        
        # Update last_active_at in user profile
        try:
            supabase_admin = get_supabase_admin()
            supabase_admin.table('user_profiles').update({
                'last_active_at': 'now()'
            }).eq('user_id', str(user.id)).execute()
        except Exception as e:
            logger.warning(f"Failed to update last_active_at: {e}")
        
        return AuthResponse(
            access_token=session.access_token,
            token_type="bearer",
            expires_in=session.expires_in or 3600,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                display_name=display_name
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        
        # Handle specific Supabase auth errors
        if "invalid login credentials" in error_msg or "invalid password" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        elif "email not confirmed" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not confirmed. Please check your inbox."
            )
        else:
            logger.error(f"Login error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed. Please try again."
            )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    auth_context: AuthContext = Depends(get_current_user)
):
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
async def get_me(
    auth_context: AuthContext = Depends(get_current_user)
):
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
        display_name=auth_context.display_name
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    authorization: Optional[str] = Header(None)
):
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
            headers={"WWW-Authenticate": "Bearer"}
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
            expires_in=3600  # This should come from token claims
        )
        
    except AuthenticationError:
        # Token is expired - in production, use refresh token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    """
    Request password reset email.
    
    Sends a password reset email to the user.
    
    Args:
        email: User's email address
        
    Returns:
        Success message
    """
    supabase = get_supabase()
    
    try:
        # Request password reset
        supabase.auth.reset_password_email(email)
        
        return {"message": "Password reset email sent. Check your inbox."}
        
    except Exception as e:
        # Don't reveal if email exists or not for security
        logger.warning(f"Password reset request for {email}: {e}")
        return {"message": "If an account exists with this email, a password reset link has been sent."}


@router.get("/verify")
async def verify_token(
    auth_context: AuthContext = Depends(get_current_user)
):
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
            "display_name": auth_context.display_name
        }
    }
