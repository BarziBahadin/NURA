import hmac

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings
from core.auth import create_admin_token, get_admin_identity, is_valid_api_key
from core.logger import log_security_event


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class LoginBody(BaseModel):
    username: str = Field(..., max_length=128)
    password: str = Field(..., max_length=256)


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(body: LoginBody, request: Request):
    if not settings.admin_password:
        await log_security_event("admin_login_disabled", body.username, request.client.host if request.client else "")
        raise HTTPException(status_code=503, detail="Admin login is not configured")

    # Evaluate both digests before combining to avoid short-circuit timing leak
    user_ok = hmac.compare_digest(body.username, settings.admin_username)
    pass_ok = hmac.compare_digest(body.password, settings.admin_password)
    if not (user_ok and pass_ok):
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
