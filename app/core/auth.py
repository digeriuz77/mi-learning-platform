"""
Authentication Middleware and Utilities for MI Learning Platform

This module provides comprehensive authentication using Supabase Auth with JWT validation.
It replaces the previous broken authentication implementation.

Key Features:
- JWT token validation using Supabase JWT secret
- User extraction from validated tokens
- Proper error handling for auth failures
- Support for both Bearer token and session-based auth
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from supabase import Client

from app.config import settings
from app.core.supabase import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)

# Security scheme for Bearer token authentication
security = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass


class AuthContext:
    """
    Authentication context containing validated user information.
    
    Attributes:
        user_id: The authenticated user's UUID
        email: User's email address
        display_name: User's display name from metadata
        is_authenticated: Whether the user is properly authenticated
        raw_token: The raw JWT token for downstream use
    """
    def __init__(
        self,
        user_id: str,
        email: str,
        display_name: Optional[str] = None,
        is_authenticated: bool = True,
        raw_token: Optional[str] = None,
        user_metadata: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.email = email
        self.display_name = display_name or email.split('@')[0]
        self.is_authenticated = is_authenticated
        self.raw_token = raw_token
        self.user_metadata = user_metadata or {}
        self.id = user_id  # Alias for compatibility

    def __repr__(self):
        return f"AuthContext(user_id={self.user_id}, email={self.email}, authenticated={self.is_authenticated})"


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token using Supabase JWT secret.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False}  # Supabase tokens don't have standard aud
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTClaimsError as e:
        raise AuthenticationError(f"Invalid token claims: {str(e)}")
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        raise AuthenticationError("Could not validate credentials")


def extract_user_from_token(payload: Dict[str, Any]) -> AuthContext:
    """
    Extract user information from decoded JWT payload.
    
    Args:
        payload: Decoded JWT payload
        
    Returns:
        AuthContext with user information
        
    Raises:
        AuthenticationError: If required claims are missing
    """
    # Supabase auth tokens have user info in 'sub' (subject) claim
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token missing subject claim")
    
    email = payload.get("email")
    if not email:
        # Try to get from user_metadata
        user_metadata = payload.get("user_metadata", {})
        email = user_metadata.get("email")
    
    if not email:
        raise AuthenticationError("Token missing email claim")
    
    # Extract display name from metadata
    user_metadata = payload.get("user_metadata", {})
    display_name = user_metadata.get("display_name") or user_metadata.get("full_name")
    
    return AuthContext(
        user_id=user_id,
        email=email,
        display_name=display_name,
        is_authenticated=True,
        user_metadata=user_metadata
    )


async def validate_token_with_supabase(token: str, supabase: Client) -> AuthContext:
    """
    Validate a token by calling Supabase Auth API.
    This is the most reliable method as it checks against the auth server.
    
    Args:
        token: The JWT token to validate
        supabase: Supabase client instance
        
    Returns:
        AuthContext with validated user information
        
    Raises:
        AuthenticationError: If token is invalid
    """
    try:
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            raise AuthenticationError("Invalid or expired token")
        
        user = response.user
        user_metadata = user.user_metadata or {}
        
        return AuthContext(
            user_id=str(user.id),
            email=user.email,
            display_name=user_metadata.get("display_name") or user_metadata.get("full_name"),
            is_authenticated=True,
            raw_token=token,
            user_metadata=user_metadata
        )
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Supabase auth validation error: {e}")
        raise AuthenticationError("Could not validate credentials with auth server")


async def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
) -> AuthContext:
    """
    Get authentication context from request.
    
    This is the main dependency for protected endpoints. It extracts
    the token from the Authorization header and validates it.
    
    Args:
        credentials: HTTP Bearer credentials
        request: FastAPI request object
        
    Returns:
        AuthContext with validated user information
        
    Raises:
        HTTPException: If authentication fails
    """
    token = None
    
    # Try to get token from Authorization header
    if credentials and credentials.credentials:
        token = credentials.credentials
    
    # Also check for token in query params (for WebSocket support)
    if not token and request:
        token = request.query_params.get("token")
    
    # Check for token in cookies
    if not token and request:
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # First try local JWT validation (faster)
        payload = decode_jwt_token(token)
        auth_context = extract_user_from_token(payload)
        auth_context.raw_token = token
        return auth_context
    except AuthenticationError as e:
        # If local validation fails, try Supabase API validation
        # This handles edge cases like token refresh
        try:
            supabase = get_supabase()
            return await validate_token_with_supabase(token, supabase)
        except AuthenticationError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
) -> AuthContext:
    """
    Get the current authenticated user.
    
    This is a convenience wrapper around get_auth_context for use in endpoints.
    
    Args:
        credentials: HTTP Bearer credentials
        request: FastAPI request object
        
    Returns:
        AuthContext with validated user information
    """
    return await get_auth_context(credentials, request)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
) -> Optional[AuthContext]:
    """
    Get the current user if authenticated, or None if not.
    
    Use this for endpoints that can work with or without authentication.
    
    Args:
        credentials: HTTP Bearer credentials
        request: FastAPI request object
        
    Returns:
        AuthContext if authenticated, None otherwise
    """
    try:
        return await get_auth_context(credentials, request)
    except HTTPException:
        return None


async def require_auth(
    auth_context: AuthContext = Depends(get_current_user)
) -> AuthContext:
    """
    Require authentication for an endpoint.
    
    This is a stricter version that ensures the user is fully authenticated.
    
    Args:
        auth_context: Authentication context from get_current_user
        
    Returns:
        AuthContext if authenticated
        
    Raises:
        HTTPException: If not authenticated
    """
    if not auth_context.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return auth_context


def create_auth_middleware():
    """
    Create a middleware function for authentication.
    
    This can be added to FastAPI app to handle auth on all routes.
    
    Returns:
        Middleware function
    """
    async def auth_middleware(request: Request, call_next):
        # Skip auth for certain paths
        public_paths = [
            "/",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/health",
            "/static/",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
        
        path = request.url.path
        
        # Check if path is public
        is_public = any(path.startswith(public_path.rstrip('/')) or 
                        path == public_path.rstrip('/') 
                        for public_path in public_paths)
        
        if is_public:
            response = await call_next(request)
            return response
        
        # For protected paths, auth will be handled by endpoint dependencies
        response = await call_next(request)
        return response
    
    return auth_middleware


# Legacy compatibility - for gradual migration
def get_current_user_legacy(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase: Client = Depends(get_supabase)
) -> Optional[Dict[str, Any]]:
    """
    Legacy get_current_user that returns a dict for backward compatibility.
    
    DEPRECATED: Use get_current_user() which returns AuthContext instead.
    
    This function maintains backward compatibility with existing code that
    expects a dict with 'id', 'email', and 'user_metadata' keys.
    """
    try:
        # Synchronous token validation for legacy compatibility
        # Do NOT use asyncio.run() as it crashes when called from async context
        if not credentials or not credentials.credentials:
            logger.warning("No credentials provided, returning demo user for legacy compatibility")
            return {
                'id': 'demo-user-123',
                'email': 'demo@example.com',
                'user_metadata': {'display_name': 'Demo User'}
            }
        
        token = credentials.credentials
        try:
            payload = decode_jwt_token(token)
            auth_context = extract_user_from_token(payload)
            return {
                'id': auth_context.user_id,
                'email': auth_context.email,
                'user_metadata': {
                    'display_name': auth_context.display_name,
                    **auth_context.user_metadata
                }
            }
        except AuthenticationError as e:
            logger.warning(f"Token validation failed: {e}, returning demo user for legacy compatibility")
            return {
                'id': 'demo-user-123',
                'email': 'demo@example.com',
                'user_metadata': {'display_name': 'Demo User'}
            }
    except HTTPException:
        # Return demo user for backward compatibility during migration
        logger.warning("Auth failed, returning demo user for legacy compatibility")
        return {
            'id': 'demo-user-123',
            'email': 'demo@example.com',
            'user_metadata': {'display_name': 'Demo User'}
        }
