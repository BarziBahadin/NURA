from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth import create_admin_token, get_admin_identity, hash_password, is_valid_api_key, verify_db_password
from core.logger import log_security_event

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class LoginBody(BaseModel):
    username: str = Field(..., max_length=128)
    password: str = Field(..., max_length=256)


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(body: LoginBody, request: Request):
    ip = request.client.host if request.client else ""
    user = await verify_db_password(body.username, body.password)
    if not user:
        await log_security_event("admin_login_failed", body.username, ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    from db.postgres import get_db_pool
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE admin_users SET last_login = NOW() WHERE username = $1",
                body.username,
            )
    except Exception:
        pass

    token = create_admin_token(body.username, role=user["role"])
    await log_security_event("admin_login_success", body.username, ip)
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@router.get("/auth/me")
async def me(request: Request):
    if is_valid_api_key(request):
        return {"type": "api_key", "role": "admin"}
    identity = get_admin_identity(request)
    if not identity:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {
        "type": "admin_token",
        "username": identity["sub"],
        "role": identity["role"],
        "display_name": identity.get("display_name", ""),
    }


async def seed_admin_user() -> None:
    """Seed the initial admin account from settings if admin_users is empty."""
    from config import settings
    from db.postgres import get_db_pool
    if not settings.admin_password:
        return
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM admin_users")
            if count == 0:
                await conn.execute(
                    "INSERT INTO admin_users (username, password_hash, role, display_name) "
                    "VALUES ($1, $2, 'admin', $3)",
                    settings.admin_username,
                    hash_password(settings.admin_password),
                    settings.admin_username,
                )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f"seed_admin_user failed: {exc}")
