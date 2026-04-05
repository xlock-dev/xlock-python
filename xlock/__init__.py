"""
xlock — invisible bot protection middleware for Python

Supports FastAPI/Starlette, Django, and Flask.

FastAPI:
    from xlock import XLockMiddleware
    app.add_middleware(XLockMiddleware, site_key="sk_...", protected_paths=["/api/auth"])

Django (settings.py):
    MIDDLEWARE = ["xlock.XLockDjangoMiddleware", ...]
    XLOCK_SITE_KEY = "sk_..."
    XLOCK_PROTECTED_PATHS = ["/api/auth/"]

Flask:
    from xlock import XLockFlask
    xlock = XLockFlask(app, site_key="sk_...", protected_paths=["/api/auth"])
"""

from xlock.middleware import XLockDjangoMiddleware, XLockFlask
from xlock.verify import verify, verify_async

__all__ = [
    "XLockMiddleware",
    "XLockDjangoMiddleware",
    "XLockFlask",
    "verify",
    "verify_async",
]
__version__ = "0.1.0"


def __getattr__(name: str):
    if name == "XLockMiddleware":
        from xlock.middleware import XLockMiddleware

        return XLockMiddleware
    raise AttributeError(f"module 'xlock' has no attribute {name!r}")
