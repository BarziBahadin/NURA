from fastapi import HTTPException, Request

from config import settings


def verify_api_key(request: Request) -> None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
