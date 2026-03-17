# bsvibe-auth (Python)

Unified authentication package for the BSVibe ecosystem — built on Supabase Auth.

## Installation

```bash
pip install git+https://github.com/bsvibe/bsvibe-auth.git#subdirectory=python

# With FastAPI helpers
pip install "bsvibe-auth[fastapi] @ git+https://github.com/bsvibe/bsvibe-auth.git#subdirectory=python"
```

## Quick Start

### Token Verification

```python
from bsvibe_auth import SupabaseAuthProvider, AuthError

auth = SupabaseAuthProvider(
    jwt_secret="your-supabase-jwt-secret",
)

try:
    user = await auth.verify_token(token)
    print(f"Authenticated: {user.id} ({user.email})")
except AuthError as e:
    print(f"Auth failed: {e.message}")
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from bsvibe_auth import SupabaseAuthProvider, BSVibeUser
from bsvibe_auth.fastapi import create_auth_dependency

app = FastAPI()

auth = SupabaseAuthProvider(
    jwt_secret="your-supabase-jwt-secret",
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
    jwt_secret="...",
    supabase_url="https://xxx.supabase.co",
    service_role_key="your-service-role-key",
)

user = await auth.get_user("user-uuid")
```

## Migration

When transitioning from Supabase Auth to a custom solution:

1. Create a new implementation inheriting from `AuthProvider` (e.g. `CustomAuthProvider`)
2. Replace `SupabaseAuthProvider` with `CustomAuthProvider` in your service code
3. No changes needed in service logic (the interface remains the same)

## Environment Variables

```env
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```
