"""Basic tests for SupabaseAuthProvider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from bsvibe_auth import (
    AuthError,
    BSVibeUser,
    SupabaseAuthProvider,
    TokenExpiredError,
    TokenInvalidError,
)

TEST_SECRET = "test-secret-key-for-unit-tests"

# Generate an EC key pair for ES256 tests
_ec_private_key = ec.generate_private_key(ec.SECP256R1())
_ec_public_key = _ec_private_key.public_key()


def _make_token(
    sub: str = "user-123",
    email: str = "test@bsvibe.dev",
    role: str = "authenticated",
    expired: bool = False,
    algorithm: str = "HS256",
    key: object | None = None,
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
    signing_key = key if key is not None else TEST_SECRET
    return pyjwt.encode(payload, signing_key, algorithm=algorithm)


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


# --- ES256 / JWKS tests ---


def _mock_jwks_provider() -> SupabaseAuthProvider:
    """Create a provider with supabase_url and a mocked JWKS client."""
    provider = SupabaseAuthProvider(supabase_url="https://test.supabase.co")

    mock_jwk = MagicMock()
    mock_jwk.key = _ec_public_key

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_jwk
    provider._jwks_client = mock_client

    return provider


@pytest.mark.asyncio
async def test_jwks_verify_valid_es256_token() -> None:
    provider = _mock_jwks_provider()
    token = _make_token(algorithm="ES256", key=_ec_private_key)
    user = await provider.verify_token(token)

    assert isinstance(user, BSVibeUser)
    assert user.id == "user-123"
    assert user.email == "test@bsvibe.dev"


@pytest.mark.asyncio
async def test_jwks_verify_expired_es256_token() -> None:
    provider = _mock_jwks_provider()
    token = _make_token(algorithm="ES256", key=_ec_private_key, expired=True)

    with pytest.raises(TokenExpiredError):
        await provider.verify_token(token)


@pytest.mark.asyncio
async def test_jwks_client_error_raises_auth_error() -> None:
    provider = SupabaseAuthProvider(supabase_url="https://test.supabase.co")
    provider._jwks_client = MagicMock()
    provider._jwks_client.get_signing_key_from_jwt.side_effect = (
        pyjwt.PyJWKClientError("JWKS endpoint unreachable")
    )

    token = _make_token(algorithm="ES256", key=_ec_private_key)
    with pytest.raises(AuthError, match="JWKS error"):
        await provider.verify_token(token)


@pytest.mark.asyncio
async def test_hs256_still_works_without_supabase_url() -> None:
    """Backward compatibility: jwt_secret only → HS256."""
    provider = SupabaseAuthProvider(jwt_secret=TEST_SECRET)
    token = _make_token()
    user = await provider.verify_token(token)

    assert user.id == "user-123"
    assert provider._jwks_client is None


@pytest.mark.asyncio
async def test_supabase_url_takes_priority_over_jwt_secret() -> None:
    """When both are provided, JWKS is used."""
    provider = SupabaseAuthProvider(
        jwt_secret=TEST_SECRET,
        supabase_url="https://test.supabase.co",
    )
    assert provider._jwks_client is not None
    assert provider._algorithms == ["ES256"]


@pytest.mark.asyncio
async def test_jwks_url_constructed_correctly() -> None:
    with patch("jwt.PyJWKClient") as mock_cls:
        SupabaseAuthProvider(supabase_url="https://test.supabase.co")
        mock_cls.assert_called_once_with(
            "https://test.supabase.co/auth/v1/.well-known/jwks.json"
        )


@pytest.mark.asyncio
async def test_jwks_url_strips_trailing_slash() -> None:
    with patch("jwt.PyJWKClient") as mock_cls:
        SupabaseAuthProvider(supabase_url="https://test.supabase.co/")
        mock_cls.assert_called_once_with(
            "https://test.supabase.co/auth/v1/.well-known/jwks.json"
        )
