import secrets

from fastapi import HTTPException, Request

from config import settings


def is_valid_api_key(request: Request) -> bool:
    if not settings.api_key:
        return False
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    return secrets.compare_digest(auth[7:], settings.api_key)


def verify_api_key(request: Request) -> None:
    if not is_valid_api_key(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
