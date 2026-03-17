"""BSVibe authentication exceptions."""


class AuthError(Exception):
    """Base exception raised on authentication failure."""

    def __init__(self, message: str = "Authentication failed") -> None:
        self.message = message
        super().__init__(self.message)


class TokenExpiredError(AuthError):
    """Raised when the token has expired."""

    def __init__(self) -> None:
        super().__init__("Token has expired")


class TokenInvalidError(AuthError):
    """Raised when the token is invalid."""

    def __init__(self, detail: str = "") -> None:
        msg = f"Invalid token: {detail}" if detail else "Invalid token"
        super().__init__(msg)
