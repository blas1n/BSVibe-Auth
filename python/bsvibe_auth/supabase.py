"""Supabase Auth provider implementation."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import jwt

from bsvibe_auth.errors import AuthError, TokenExpiredError, TokenInvalidError
from bsvibe_auth.models import BSVibeUser
from bsvibe_auth.provider import AuthProvider


class SupabaseAuthProvider(AuthProvider):
    """Supabase Auth JWT verification provider.

    Supports two verification modes:

    - **JWKS (recommended):** Pass ``supabase_url`` to automatically fetch
      the public key from the project's JWKS endpoint and verify ES256 tokens.
    - **HS256 (legacy):** Pass ``jwt_secret`` to verify tokens with a
      symmetric secret. Used when ``supabase_url`` is not provided.

    If both ``supabase_url`` and ``jwt_secret`` are provided, JWKS takes
    priority for token verification.

    Args:
        jwt_secret: JWT Secret for HS256 verification.
        supabase_url: Supabase project URL (e.g. https://xxx.supabase.co).
                    Enables JWKS-based ES256 verification and Admin API calls.
        service_role_key: Supabase service_role key for Admin API calls.
        algorithms: JWT signing algorithms. Defaults to ``["ES256"]`` when
                    using JWKS, ``["HS256"]`` otherwise.
    """

    def __init__(
        self,
        jwt_secret: str = "",
        supabase_url: str | None = None,
        service_role_key: str | None = None,
        algorithms: list[str] | None = None,
    ) -> None:
        self._jwt_secret = jwt_secret
        self._supabase_url = supabase_url.rstrip("/") if supabase_url else None
        self._service_role_key = service_role_key
        self._jwks_client: jwt.PyJWKClient | None = None

        if self._supabase_url:
            jwks_url = f"{self._supabase_url}/auth/v1/.well-known/jwks.json"
            self._jwks_client = jwt.PyJWKClient(jwks_url)
            self._algorithms = algorithms or ["ES256"]
        else:
            self._algorithms = algorithms or ["HS256"]

    async def verify_token(self, token: str) -> BSVibeUser:
        """Verify a Supabase JWT and return a BSVibeUser."""
        try:
            if self._jwks_client:
                signing_key = self._jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=self._algorithms,
                    audience="authenticated",
                )
            else:
                payload = jwt.decode(
                    token,
                    self._jwt_secret,
                    algorithms=self._algorithms,
                    audience="authenticated",
                )
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.PyJWKClientError as e:
            raise AuthError(f"JWKS error: {e}")
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError(str(e))

        return self._payload_to_user(payload)

    async def get_user(self, user_id: str) -> BSVibeUser | None:
        """Look up user information via the Supabase Admin API."""
        if not self._supabase_url or not self._service_role_key:
            raise AuthError(
                "supabase_url and service_role_key are required for get_user()"
            )

        url = f"{self._supabase_url}/auth/v1/admin/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {self._service_role_key}",
            "apikey": self._service_role_key,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise AuthError(f"Supabase Admin API error: {resp.status_code}")

        data = resp.json()
        return BSVibeUser(
            id=data["id"],
            email=data.get("email"),
            role=data.get("role", "authenticated"),
            app_metadata=data.get("app_metadata", {}),
            user_metadata=data.get("user_metadata", {}),
        )

    @staticmethod
    def _payload_to_user(payload: dict) -> BSVibeUser:
        """Convert a JWT payload to a BSVibeUser."""
        iat = payload.get("iat")
        exp = payload.get("exp")

        return BSVibeUser(
            id=payload["sub"],
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
            app_metadata=payload.get("app_metadata", {}),
            user_metadata=payload.get("user_metadata", {}),
            issued_at=datetime.fromtimestamp(iat, tz=UTC) if iat else None,
            expires_at=datetime.fromtimestamp(exp, tz=UTC) if exp else None,
        )
