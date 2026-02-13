"""
CSRF protection utilities for the application.
Provides dependency-based CSRF validation for state-changing operations.
"""

from fastapi import Request, HTTPException, status
from typing import Optional

CSRF_TOKEN_HEADER = "X-CSRF-Token"
CSRF_COOKIE_NAME = "csrf_token"


async def csrf_protect(request: Request) -> None:
    """
    CSRF protection dependency.

    Validates CSRF token for requests that include authentication via cookie.
    Skip validation for:
    - GET, HEAD, OPTIONS requests (safe methods)
    - Requests using Authorization header (not cookie-based)
    - Anonymous endpoints

    Usage:
        @app.post("/endpoint")
        async def endpoint(request: Request, _: None = Depends(csrf_protect)):
            ...
    """
    # Skip for safe methods
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Check if using cookie-based auth (the vulnerability vector)
    token_from_cookie = request.cookies.get("access_token")
    if not token_from_cookie:
        # Not using cookie auth, skip CSRF check
        return

    # For cookie-based auth, require CSRF token
    csrf_token = request.headers.get(CSRF_TOKEN_HEADER)

    if not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token required. Include 'X-CSRF-Token' header."
        )

    # Validate CSRF token matches
    # In production, store the CSRF token in a server-side session or verify against a signed cookie
    # For now, we require the token to be present (basic protection)
    # A more robust implementation would verify the token against a stored value

    return


def get_csrf_token_for_response() -> str:
    """
    Generate a CSRF token for the response.
    In a full implementation, this would generate and sign a token.
    """
    import uuid

    return uuid.uuid4().hex
