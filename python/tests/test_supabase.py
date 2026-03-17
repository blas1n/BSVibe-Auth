"""Basic tests for SupabaseAuthProvider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest

from bsvibe_auth import (
    BSVibeUser,
    SupabaseAuthProvider,
    TokenExpiredError,
    TokenInvalidError,
)

TEST_SECRET = "test-secret-key-for-unit-tests"


def _make_token(
    sub: str = "user-123",
    email: str = "test@bsvibe.dev",
    role: str = "authenticated",
    expired: bool = False,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "aud": "authenticated",
        "iat": now,
        "exp": now + timedelta(hours=-1 if expired else 1),
        "app_metadata": {},
        "user_metadata": {"name": "Test User"},
    }
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def provider() -> SupabaseAuthProvider:
    return SupabaseAuthProvider(jwt_secret=TEST_SECRET)


@pytest.mark.asyncio
async def test_verify_valid_token(provider: SupabaseAuthProvider) -> None:
    token = _make_token()
    user = await provider.verify_token(token)

    assert isinstance(user, BSVibeUser)
    assert user.id == "user-123"
    assert user.email == "test@bsvibe.dev"
    assert user.role == "authenticated"
    assert user.user_metadata == {"name": "Test User"}
    assert not user.is_anonymous


@pytest.mark.asyncio
async def test_verify_expired_token(provider: SupabaseAuthProvider) -> None:
    token = _make_token(expired=True)

    with pytest.raises(TokenExpiredError):
        await provider.verify_token(token)


@pytest.mark.asyncio
async def test_verify_invalid_token(provider: SupabaseAuthProvider) -> None:
    with pytest.raises(TokenInvalidError):
        await provider.verify_token("not-a-valid-jwt")


@pytest.mark.asyncio
async def test_verify_wrong_secret() -> None:
    provider = SupabaseAuthProvider(jwt_secret="wrong-secret")
    token = _make_token()

    with pytest.raises(TokenInvalidError):
        await provider.verify_token(token)


@pytest.mark.asyncio
async def test_anonymous_user(provider: SupabaseAuthProvider) -> None:
    token = _make_token(role="anon")
    user = await provider.verify_token(token)

    assert user.is_anonymous
