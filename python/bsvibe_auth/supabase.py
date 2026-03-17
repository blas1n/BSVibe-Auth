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

    Args:
        jwt_secret: JWT Secret for your Supabase project.
                    Found in Supabase Dashboard > Settings > API > JWT Secret.
        supabase_url: Supabase project URL (e.g. https://xxx.supabase.co).
                    Used for Admin API calls in get_user().
        service_role_key: Supabase service_role key.
                        Used for Admin API calls in get_user().
                        Not required if only using verify_token().
        algorithms: JWT signing algorithm. Supabase default is HS256.
    """

    def __init__(
        self,
        jwt_secret: str,
        supabase_url: str | None = None,
        service_role_key: str | None = None,
        algorithms: list[str] | None = None,
    ) -> None:
        self._jwt_secret = jwt_secret
        self._supabase_url = supabase_url.rstrip("/") if supabase_url else None
        self._service_role_key = service_role_key
        self._algorithms = algorithms or ["HS256"]

    async def verify_token(self, token: str) -> BSVibeUser:
        """Verify a Supabase JWT and return a BSVibeUser."""
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=self._algorithms,
                audience="authenticated",
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
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
