"""Abstract authentication provider interface.

When migrating from Supabase Auth to a custom solution,
only the implementation needs to be swapped — no service code changes required.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from bsvibe_auth.models import BSVibeUser


class AuthProvider(ABC):
    """Unified authentication provider interface for BSVibe."""

    @abstractmethod
    async def verify_token(self, token: str) -> BSVibeUser:
        """Verify a Bearer token and return user information.

        Args:
            token: JWT access token (without the Bearer prefix).

        Returns:
            Verified user information.

        Raises:
            AuthError: If the token is invalid or expired.
        """
        ...

    @abstractmethod
    async def get_user(self, user_id: str) -> BSVibeUser | None:
        """Look up user information by user_id.

        Args:
            user_id: Supabase Auth user ID (UUID).

        Returns:
            User information, or None if not found.
        """
        ...
