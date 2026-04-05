"""
Core x-lock verification — usable standalone without any framework.
"""

import json
import urllib.request
import urllib.error
from typing import Optional

DEFAULT_API_URL = "https://api.x-lock.dev"


class VerifyResult:
    __slots__ = ("blocked", "reason", "error")

    def __init__(self, blocked: bool = False, reason: Optional[str] = None, error: bool = False):
        self.blocked = blocked
        self.reason = reason
        self.error = error


def verify(
    token: str,
    site_key: str,
    path: Optional[str] = None,
    api_url: str = DEFAULT_API_URL,
) -> VerifyResult:
    """Synchronously verify an x-lock token. Works with stdlib only."""
    if token.startswith("v3."):
        session_id = token.split(".")[1]
        enforce_url = f"{api_url}/v3/session/enforce"
        body = {"sessionId": session_id, "siteKey": site_key}
    else:
        enforce_url = f"{api_url}/v1/enforce"
        body = {"token": token, "siteKey": site_key}

    if path:
        body["path"] = path

    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        enforce_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5):
            return VerifyResult(blocked=False)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            data = json.loads(e.read().decode())
            return VerifyResult(blocked=True, reason=data.get("reason"))
        return VerifyResult(blocked=False, error=True)
    except Exception:
        return VerifyResult(blocked=False, error=True)


async def verify_async(
    token: str,
    site_key: str,
    path: Optional[str] = None,
    api_url: str = DEFAULT_API_URL,
) -> VerifyResult:
    """Async verify using httpx. Requires: pip install xlock[fastapi]"""
    import httpx

    if token.startswith("v3."):
        session_id = token.split(".")[1]
        enforce_url = f"{api_url}/v3/session/enforce"
        body = {"sessionId": session_id, "siteKey": site_key}
    else:
        enforce_url = f"{api_url}/v1/enforce"
        body = {"token": token, "siteKey": site_key}

    if path:
        body["path"] = path

    async with httpx.AsyncClient(timeout=5) as client:
        res = await client.post(enforce_url, json=body)

    if res.status_code == 403:
        data = res.json()
        return VerifyResult(blocked=True, reason=data.get("reason"))

    if not res.is_success:
        return VerifyResult(blocked=False, error=True)

    return VerifyResult(blocked=False)
