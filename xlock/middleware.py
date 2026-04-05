"""
x-lock middleware implementations for FastAPI/Starlette, Django, and Flask.
"""

import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger("x-lock")

DEFAULT_API_URL = "https://api.x-lock.dev"


# ─── FastAPI / Starlette ───

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    import httpx

    class XLockMiddleware(BaseHTTPMiddleware):
        """
        x-lock middleware for FastAPI / Starlette.

        Usage:
            from xlock import XLockMiddleware
            app.add_middleware(
                XLockMiddleware,
                site_key="sk_...",
                protected_paths=["/api/auth", "/api/checkout"],
            )
        """

        def __init__(self, app, **kwargs):
            super().__init__(app)
            self.api_url = kwargs.get("api_url", DEFAULT_API_URL)
            self.site_key = kwargs.get("site_key") or os.environ.get("XLOCK_SITE_KEY")
            self.fail_open = kwargs.get("fail_open", True)
            self.protected_paths: list = kwargs.get("protected_paths", [])

            if not self.site_key:
                logger.warning("No site key configured — skipping enforcement")

        def _matches(self, path: str) -> bool:
            return any(path.startswith(p) for p in self.protected_paths)

        async def dispatch(self, request: Request, call_next):
            if not self.site_key:
                return await call_next(request)
            if request.method != "POST":
                return await call_next(request)
            if self.protected_paths and not self._matches(request.url.path):
                return await call_next(request)

            token = request.headers.get("x-lock")

            if not token:
                return JSONResponse(
                    {"error": "Blocked by x-lock: missing token"}, status_code=403
                )

            try:
                if token.startswith("v3."):
                    session_id = token.split(".")[1]
                    enforce_url = f"{self.api_url}/v3/session/enforce"
                    enforce_body = {"sessionId": session_id, "siteKey": self.site_key, "path": str(request.url.path)}
                else:
                    enforce_url = f"{self.api_url}/v1/enforce"
                    enforce_body = {"token": token, "siteKey": self.site_key, "path": str(request.url.path)}

                async with httpx.AsyncClient(timeout=5) as client:
                    res = await client.post(
                        enforce_url,
                        json=enforce_body,
                    )

                if res.status_code == 403:
                    data = res.json()
                    return JSONResponse(
                        {"error": "Blocked by x-lock", "reason": data.get("reason")},
                        status_code=403,
                    )

                if not res.is_success and not self.fail_open:
                    return JSONResponse(
                        {"error": "x-lock verification failed"}, status_code=403
                    )

            except Exception as e:
                logger.error(f"Enforcement error: {e}")
                if not self.fail_open:
                    return JSONResponse(
                        {"error": "x-lock verification failed"}, status_code=403
                    )

            return await call_next(request)

except ImportError:
    # Starlette/httpx not installed — provide a stub
    class XLockMiddleware:  # type: ignore[no-redef]
        """Stub — install starlette and httpx for FastAPI support."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Install starlette and httpx for FastAPI/Starlette support: "
                "pip install xlock[fastapi]"
            )


# ─── Django ───

class XLockDjangoMiddleware:
    """
    x-lock middleware for Django.

    Usage (settings.py):
        MIDDLEWARE = ["xlock.XLockDjangoMiddleware", ...]
        XLOCK_SITE_KEY = "sk_..."
        XLOCK_PROTECTED_PATHS = ["/api/auth/", "/api/checkout/"]
        XLOCK_API_URL = "https://api.x-lock.dev"  # optional
        XLOCK_FAIL_OPEN = True  # optional
    """

    def __init__(self, get_response):
        self.get_response = get_response

        try:
            from django.conf import settings as django_settings

            self.api_url = getattr(django_settings, "XLOCK_API_URL", DEFAULT_API_URL)
            self.site_key = getattr(django_settings, "XLOCK_SITE_KEY", None) or os.environ.get("XLOCK_SITE_KEY")
            self.fail_open = getattr(django_settings, "XLOCK_FAIL_OPEN", True)
            self.protected_paths = getattr(django_settings, "XLOCK_PROTECTED_PATHS", [])
        except Exception:
            self.api_url = os.environ.get("XLOCK_API_URL", DEFAULT_API_URL)
            self.site_key = os.environ.get("XLOCK_SITE_KEY")
            self.fail_open = True
            self.protected_paths = []

        if not self.site_key:
            logger.warning("No site key configured — skipping enforcement")

    def __call__(self, request):
        if self.site_key and request.method == "POST":
            if not self.protected_paths or self._matches(request.path):
                result = self._enforce(request)
                if result is not None:
                    return result

        return self.get_response(request)

    def _matches(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.protected_paths)

    def _enforce(self, request):
        try:
            from django.http import JsonResponse
        except ImportError:
            return None

        token = request.META.get("HTTP_X_LOCK")

        if not token:
            return JsonResponse({"error": "Blocked by x-lock: missing token"}, status=403)

        try:
            if token.startswith("v3."):
                session_id = token.split(".")[1]
                enforce_url = f"{self.api_url}/v3/session/enforce"
                payload = json.dumps({"sessionId": session_id, "siteKey": self.site_key, "path": request.path}).encode()
            else:
                enforce_url = f"{self.api_url}/v1/enforce"
                payload = json.dumps({"token": token, "siteKey": self.site_key, "path": request.path}).encode()

            req = urllib.request.Request(
                enforce_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=5) as res:
                pass  # 200 = allowed

        except urllib.error.HTTPError as e:
            if e.code == 403:
                data = json.loads(e.read().decode())
                return JsonResponse(
                    {"error": "Blocked by x-lock", "reason": data.get("reason")},
                    status=403,
                )
            if not self.fail_open:
                return JsonResponse({"error": "x-lock verification failed"}, status=403)

        except Exception as e:
            logger.error(f"Enforcement error: {e}")
            if not self.fail_open:
                return JsonResponse({"error": "x-lock verification failed"}, status=403)

        return None


# ─── Flask ───

class XLockFlask:
    """
    x-lock middleware for Flask.

    Usage:
        from xlock import XLockFlask
        app = Flask(__name__)
        xlock = XLockFlask(app, site_key="sk_...", protected_paths=["/api/auth"])
    """

    def __init__(self, app=None, **kwargs):
        self.api_url = kwargs.get("api_url", DEFAULT_API_URL)
        self.site_key = kwargs.get("site_key") or os.environ.get("XLOCK_SITE_KEY")
        self.fail_open = kwargs.get("fail_open", True)
        self.protected_paths: list = kwargs.get("protected_paths", [])

        if app:
            self.init_app(app)

    def init_app(self, app):
        if not self.site_key:
            app.logger.warning("[x-lock] No site key configured — skipping enforcement")
            return

        app.before_request(self._enforce)

    def _matches(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.protected_paths)

    def _enforce(self):
        try:
            from flask import request, jsonify
        except ImportError:
            return None

        if request.method != "POST":
            return None
        if self.protected_paths and not self._matches(request.path):
            return None

        token = request.headers.get("x-lock")

        if not token:
            return jsonify(error="Blocked by x-lock: missing token"), 403

        try:
            import httpx

            if token.startswith("v3."):
                session_id = token.split(".")[1]
                enforce_url = f"{self.api_url}/v3/session/enforce"
                enforce_body = {"sessionId": session_id, "siteKey": self.site_key, "path": request.path}
            else:
                enforce_url = f"{self.api_url}/v1/enforce"
                enforce_body = {"token": token, "siteKey": self.site_key, "path": request.path}

            with httpx.Client(timeout=5) as client:
                res = client.post(
                    enforce_url,
                    json=enforce_body,
                )

            if res.status_code == 403:
                data = res.json()
                return jsonify(error="Blocked by x-lock", reason=data.get("reason")), 403

            if not res.ok and not self.fail_open:
                return jsonify(error="x-lock verification failed"), 403

        except Exception as e:
            logger.error(f"Enforcement error: {e}")
            if not self.fail_open:
                return jsonify(error="x-lock verification failed"), 403

        return None
