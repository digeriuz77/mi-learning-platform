"""Tests for core auth context behavior."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.core import auth as auth_module


def _make_request(query_string: bytes = b"") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": query_string,
    }
    return Request(scope)


def test_get_auth_context_accepts_pytest_fixture_token(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests::auth")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token-abc")

    result = asyncio.run(auth_module.get_auth_context(credentials=creds, request=None))

    assert result.user_id == "test-user-id-123"
    assert result.email == "test@example.com"


def test_get_auth_context_rejects_malformed_token_without_supabase_call(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    validate_mock = AsyncMock()
    monkeypatch.setattr(auth_module, "validate_token_with_supabase", validate_mock)

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth_module.get_auth_context(credentials=creds, request=None))

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"
    validate_mock.assert_not_called()


def test_get_auth_context_allows_legacy_transport_when_enabled(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ALLOW_LEGACY_TOKEN_TRANSPORT", "true")

    validate_mock = AsyncMock(
        return_value=auth_module.AuthContext(user_id="u1", email="u1@example.com", raw_token="a.b.c")
    )
    monkeypatch.setattr(auth_module, "validate_token_with_supabase", validate_mock)
    monkeypatch.setattr(auth_module, "get_supabase", lambda: object())

    request = _make_request(query_string=b"token=a.b.c")

    result = asyncio.run(auth_module.get_auth_context(credentials=None, request=request))

    assert result.user_id == "u1"
    validate_mock.assert_awaited_once()


def test_get_auth_context_uses_local_fallback_only_when_enabled(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ALLOW_LOCAL_JWT_FALLBACK", "true")
    monkeypatch.setattr(auth_module.settings, "SUPABASE_JWT_SECRET", "test-secret")
    monkeypatch.setattr(auth_module, "get_supabase", lambda: object())
    monkeypatch.setattr(
        auth_module,
        "validate_token_with_supabase",
        AsyncMock(side_effect=auth_module.AuthenticationError("Invalid or expired token")),
    )
    monkeypatch.setattr(auth_module, "decode_jwt_token", lambda token: {"sub": "u2", "email": "u2@example.com"})
    monkeypatch.setattr(
        auth_module,
        "extract_user_from_token",
        lambda payload: auth_module.AuthContext(user_id=payload["sub"], email=payload["email"]),
    )

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="a.b.c")
    result = asyncio.run(auth_module.get_auth_context(credentials=creds, request=None))

    assert result.user_id == "u2"
    assert result.raw_token == "a.b.c"
