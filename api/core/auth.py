import secrets
import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import HTTPException, Request

from config import settings


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_admin_token(username: str, role: str = "admin") -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + settings.admin_token_ttl_seconds,
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(settings.admin_secret_key.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(sig)}"


def verify_admin_token(token: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    expected = _b64(hmac.new(settings.admin_secret_key.encode(), body.encode(), hashlib.sha256).digest())
    if not secrets.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_unb64(body))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return ""
    return auth[7:]


def is_valid_api_key(request: Request) -> bool:
    if not settings.api_key:
        return False
    return secrets.compare_digest(get_bearer_token(request), settings.api_key)


def get_admin_identity(request: Request) -> dict[str, Any] | None:
    return verify_admin_token(get_bearer_token(request))


def has_admin_access(request: Request, roles: set[str] | None = None) -> bool:
    if is_valid_api_key(request):
        return True
    identity = get_admin_identity(request)
    if not identity:
        return False
    if roles and identity.get("role") not in roles:
        return False
    return True


def verify_api_key(request: Request) -> None:
    if not has_admin_access(request):
        raise HTTPException(status_code=401, detail="Unauthorized")


def require_roles(*roles: str):
    role_set = set(roles)

    def dependency(request: Request) -> None:
        if not has_admin_access(request, role_set):
            raise HTTPException(status_code=403, detail="Forbidden")

    return dependency
