# bsvibe-auth (Python)

Unified authentication package for the BSVibe ecosystem — built on Supabase Auth.

## Installation

```bash
pip install git+https://github.com/bsvibe/bsvibe-auth.git#subdirectory=python

# With FastAPI helpers
pip install "bsvibe-auth[fastapi] @ git+https://github.com/bsvibe/bsvibe-auth.git#subdirectory=python"
```

## Supabase Setup

### 1. Create a Supabase Project

Go to [supabase.com/dashboard](https://supabase.com/dashboard) and create a new project.

### 2. Get Your Credentials

Navigate to **Settings > API** in your Supabase Dashboard. You'll need:

| Credential | Location | Required For |
|---|---|---|
| **Project URL** | Settings > API > Project URL | `verify_token()` (JWKS/ES256) + `get_user()` |
| **JWT Secret** | Settings > API > JWT Secret | `verify_token()` (HS256 legacy only) |
| **service_role key** | Settings > API > service_role | `get_user()` (Admin API) |

> **Note:** Supabase now uses **ES256 (ECDSA)** for JWT signing. Pass `supabase_url` to automatically verify tokens via JWKS. The legacy `jwt_secret` (HS256) mode is still supported for backward compatibility.
>
> **Warning:** The `service_role` key bypasses Row Level Security. Never expose it to the client side.

### 3. Configure Auth Providers (Optional)

In **Authentication > Providers**, enable the sign-in methods you need:

- **Email/Password** — enabled by default
- **OAuth** — Google, GitHub, Apple, etc.
- **Magic Link** — passwordless email login
- **Phone/OTP** — SMS-based auth

### 4. Set Environment Variables

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Only needed for legacy HS256 mode (when not using supabase_url for JWKS):
# SUPABASE_JWT_SECRET=your-jwt-secret
```

## Quick Start

### Token Verification (ES256 / JWKS — recommended)

```python
from bsvibe_auth import SupabaseAuthProvider, AuthError

# Automatically fetches public key from JWKS endpoint
auth = SupabaseAuthProvider(
    supabase_url="https://xxx.supabase.co",
)

try:
    user = await auth.verify_token(token)
    print(f"Authenticated: {user.id} ({user.email})")
except AuthError as e:
    print(f"Auth failed: {e.message}")
```

### Token Verification (HS256 — legacy)

```python
auth = SupabaseAuthProvider(
    jwt_secret="your-supabase-jwt-secret",
)

user = await auth.verify_token(token)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from bsvibe_auth import SupabaseAuthProvider, BSVibeUser
from bsvibe_auth.fastapi import create_auth_dependency

app = FastAPI()

auth = SupabaseAuthProvider(
    supabase_url="https://xxx.supabase.co",
    service_role_key="your-service-role-key",
)

get_current_user = create_auth_dependency(auth)


@app.get("/me")
async def me(user: BSVibeUser = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}
```

### User Lookup (Admin API)

```python
auth = SupabaseAuthProvider(
    supabase_url="https://xxx.supabase.co",
    service_role_key="your-service-role-key",
)

user = await auth.get_user("user-uuid")
```

## Real-World Project Guide

### Recommended Project Structure

```
my-bsvibe-service/
├── app/
│   ├── main.py           # FastAPI app entry point
│   ├── config.py          # Settings / env vars
│   ├── deps.py            # Shared dependencies (auth, db, etc.)
│   └── routers/
│       ├── users.py
│       └── items.py
├── pyproject.toml
└── .env
```

### Step 1: Settings with Pydantic

```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str

    class Config:
        env_file = ".env"


settings = Settings()
```

### Step 2: Auth Dependency

```python
# app/deps.py
from bsvibe_auth import SupabaseAuthProvider
from bsvibe_auth.fastapi import create_auth_dependency

from app.config import settings

auth_provider = SupabaseAuthProvider(
    supabase_url=settings.supabase_url,
    service_role_key=settings.supabase_service_role_key,
)

get_current_user = create_auth_dependency(auth_provider)
```

### Step 3: Use in Routes

```python
# app/routers/users.py
from fastapi import APIRouter, Depends
from bsvibe_auth import BSVibeUser

from app.deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(user: BSVibeUser = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "metadata": user.user_metadata,
    }


@router.get("/me/is-admin")
async def check_admin(user: BSVibeUser = Depends(get_current_user)):
    is_admin = user.app_metadata.get("role") == "admin"
    return {"is_admin": is_admin}
```

### Step 4: Role-Based Access Control

```python
# app/deps.py (add to existing file)
from fastapi import HTTPException, status


def require_role(*allowed_roles: str):
    """Create a dependency that checks user role from app_metadata."""

    async def check_role(user: BSVibeUser = Depends(get_current_user)):
        user_role = user.app_metadata.get("role", "user")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return check_role


# Usage in routes:
require_admin = require_role("admin")
require_editor = require_role("admin", "editor")


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: BSVibeUser = Depends(require_admin)):
    ...
```

### Step 5: Frontend Token Flow

The client-side app handles sign-in via Supabase JS SDK and passes the access token to your API:

```
┌──────────┐     sign in      ┌──────────────┐
│  Client   │ ───────────────► │ Supabase Auth │
│ (Browser) │ ◄─────────────── │              │
│           │   access_token   └──────────────┘
│           │
│           │  Authorization: Bearer <token>
│           │ ───────────────────────────────────►  ┌─────────────────┐
│           │                                       │  Your FastAPI   │
│           │ ◄──────────────────────────────────── │  + bsvibe-auth  │
└──────────┘         response                      └─────────────────┘
```

```javascript
// Client-side (JavaScript)
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Sign in
const { data } = await supabase.auth.signInWithPassword({
  email: "user@example.com",
  password: "password",
});

// Call your API with the access token
const res = await fetch("https://api.example.com/users/me", {
  headers: {
    Authorization: `Bearer ${data.session.access_token}`,
  },
});
```

## BSVibeUser Model

Fields available after token verification:

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Supabase Auth user ID (UUID) |
| `email` | `str \| None` | User email |
| `role` | `str` | Supabase role (`"authenticated"` or `"anon"`) |
| `app_metadata` | `dict` | Server-side metadata (roles, permissions) |
| `user_metadata` | `dict` | User-editable metadata (display name, avatar) |
| `issued_at` | `datetime \| None` | Token issue time |
| `expires_at` | `datetime \| None` | Token expiry time |
| `is_anonymous` | `bool` | `True` if role is `"anon"` (property) |

## Error Handling

| Exception | When |
|---|---|
| `AuthError` | Base exception for all auth failures |
| `TokenExpiredError` | JWT has expired — client should refresh the token |
| `TokenInvalidError` | JWT is malformed or signature verification failed |

```python
from bsvibe_auth import AuthError, TokenExpiredError, TokenInvalidError

try:
    user = await auth.verify_token(token)
except TokenExpiredError:
    # 401 — tell client to refresh token
    ...
except TokenInvalidError:
    # 401 — token is invalid, re-login required
    ...
except AuthError:
    # Catch-all for other auth failures
    ...
```

## Migration

When transitioning from Supabase Auth to a custom solution:

1. Create a new implementation inheriting from `AuthProvider` (e.g. `CustomAuthProvider`)
2. Replace `SupabaseAuthProvider` with `CustomAuthProvider` in your service code
3. No changes needed in service logic (the interface remains the same)
