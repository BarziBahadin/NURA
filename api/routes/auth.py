import hmac

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import settings
from core.auth import create_admin_token, get_admin_identity, is_valid_api_key
from core.logger import log_security_event


router = APIRouter()


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(body: LoginBody, request: Request):
    if not settings.admin_password:
        await log_security_event("admin_login_disabled", body.username, request.client.host if request.client else "")
        raise HTTPException(status_code=503, detail="Admin login is not configured")

    valid = hmac.compare_digest(body.username, settings.admin_username) and hmac.compare_digest(
        body.password,
        settings.admin_password,
    )
    if not valid:
        await log_security_event("admin_login_failed", body.username, request.client.host if request.client else "")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_admin_token(body.username, role="admin")
    await log_security_event("admin_login_success", body.username, request.client.host if request.client else "")
    return {"access_token": token, "token_type": "bearer", "role": "admin"}


@router.get("/auth/me")
async def me(request: Request):
    if is_valid_api_key(request):
        return {"type": "api_key", "role": "admin"}
    identity = get_admin_identity(request)
    if not identity:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"type": "admin_token", "username": identity["sub"], "role": identity["role"]}
