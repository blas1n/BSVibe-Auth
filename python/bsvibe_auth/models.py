"""BSVibe common user model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BSVibeUser(BaseModel):
    """User model shared across all BSVibe services.

    Contains information extracted from Supabase Auth JWT claims.
    Extend by subclassing if additional fields are needed per service.
    """

    id: str = Field(description="Supabase Auth user ID (UUID)")
    email: str | None = Field(default=None, description="User email")
    role: str = Field(default="authenticated", description="Supabase role")
    app_metadata: dict[str, Any] = Field(default_factory=dict)
    user_metadata: dict[str, Any] = Field(default_factory=dict)
    issued_at: datetime | None = Field(default=None, description="Token issued at")
    expires_at: datetime | None = Field(default=None, description="Token expires at")

    @property
    def is_anonymous(self) -> bool:
        return self.role == "anon"
