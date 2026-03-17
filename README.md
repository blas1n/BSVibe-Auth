# bsvibe-auth

Unified authentication package monorepo for the BSVibe ecosystem.

Provides JWT verification and a common user model based on Supabase Auth,
shared across all BSVibe services

## Structure

```
bsvibe-auth/
├── python/          ← For Python services (FastAPI, etc.)
└── (typescript/)    ← To be added as needed
```

## Installation (Python)

```bash
pip install git+https://github.com/bsvibe/bsvibe-auth.git#subdirectory=python
```

Or as a `pyproject.toml` dependency:

```toml
[project]
dependencies = [
    "bsvibe-auth @ git+https://github.com/bsvibe/bsvibe-auth.git#subdirectory=python",
]
```

Pin to a specific version:

```toml
"bsvibe-auth @ git+https://github.com/bsvibe/bsvibe-auth.git@v0.1.0#subdirectory=python"
```

## Usage

```python
from bsvibe_auth import SupabaseAuthProvider

auth = SupabaseAuthProvider(
    jwt_secret="your-supabase-jwt-secret",
)

# Use as a FastAPI dependency
from bsvibe_auth.fastapi import get_current_user
```

For detailed usage, see [python/README.md](python/README.md).
