"""FastAPI dependency injection helpers.

Usage:
    from bsvibe_auth.fastapi import create_auth_dependency

    get_current_user = create_auth_dependency(auth_provider)

    @app.get("/me")
    async def me(user: BSVibeUser = Depends(get_current_user)):
        return user
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from bsvibe_auth.errors import AuthError

if TYPE_CHECKING:
    from collections.abc import Callable

    from bsvibe_auth.models import BSVibeUser
    from bsvibe_auth.provider import AuthProvider

_bearer_scheme = HTTPBearer()


def create_auth_dependency(
    provider: AuthProvider,
) -> Callable:
    """Convert an AuthProvider into a FastAPI dependency.

    Args:
        provider: An AuthProvider implementation (e.g. SupabaseAuthProvider).

    Returns:
        FastAPI dependency function.
    """

    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    ) -> BSVibeUser:
        try:
            return await provider.verify_token(credentials.credentials)
        except AuthError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"},
            )

    return get_current_user
