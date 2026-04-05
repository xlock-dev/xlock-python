# xlock-py

Invisible bot protection middleware for Python. Drop-in replacement for reCAPTCHA, Turnstile, and hCaptcha — no visual challenges, no user friction.

Supports **FastAPI**, **Django**, and **Flask**.

## Install

```bash
# Core (Django — no extra deps)
pip install xlock-py

# FastAPI / Starlette
pip install xlock-py[fastapi]

# Flask
pip install xlock-py[flask]

# Everything
pip install xlock-py[all]
```

## Quick Start

### FastAPI / Starlette

```python
from fastapi import FastAPI
from xlock import XLockMiddleware

app = FastAPI()
app.add_middleware(
    XLockMiddleware,
    site_key="sk_...",
    protected_paths=["/api/auth", "/api/checkout"],
)
```

### Django

```python
# settings.py
MIDDLEWARE = [
    "xlock.XLockDjangoMiddleware",
    # ... other middleware
]

XLOCK_SITE_KEY = "sk_..."
XLOCK_PROTECTED_PATHS = ["/api/auth/", "/api/checkout/"]
```

### Flask

```python
from flask import Flask
from xlock import XLockFlask

app = Flask(__name__)
xlock = XLockFlask(app, site_key="sk_...", protected_paths=["/api/auth"])
```

### Direct Verification

```python
from xlock import verify

result = verify(token="v3.abc123...", site_key="sk_...", path="/api/login")
if result.blocked:
    print(f"Blocked: {result.reason}")
```

## Configuration

| Option | Env Var | Default | Description |
|--------|---------|---------|-------------|
| `site_key` | `XLOCK_SITE_KEY` | — | Your x-lock site key |
| `api_url` | `XLOCK_API_URL` | `https://api.x-lock.dev` | API endpoint |
| `fail_open` | `XLOCK_FAIL_OPEN` | `True` | Allow requests on API errors |
| `protected_paths` | `XLOCK_PROTECTED_PATHS` | `[]` | Path prefixes to protect |

## License

MIT
