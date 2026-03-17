"""bsvibe-auth: Unified authentication package for the BSVibe ecosystem."""

from bsvibe_auth.errors import AuthError, TokenExpiredError, TokenInvalidError
from bsvibe_auth.models import BSVibeUser
from bsvibe_auth.provider import AuthProvider
from bsvibe_auth.supabase import SupabaseAuthProvider

__all__ = [
    "AuthError",
    "AuthProvider",
    "BSVibeUser",
    "SupabaseAuthProvider",
    "TokenExpiredError",
    "TokenInvalidError",
]
