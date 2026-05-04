from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth import get_admin_identity, hash_password, require_roles
from core.session_manager import get_redis
from config import settings
from db.postgres import get_db_pool

router = APIRouter()


class CreateUserBody(BaseModel):
    username: str = Field(..., max_length=64, pattern=r'^[a-zA-Z0-9_]+$')
    password: str = Field(..., min_length=8, max_length=256)
    role: str = Field(default="agent")
    display_name: str = Field(default="", max_length=128)


class UpdateUserBody(BaseModel):
    role: Optional[str] = None
    display_name: Optional[str] = Field(default=None, max_length=128)
    is_active: Optional[bool] = None


class ResetPasswordBody(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=256)


async def _audit(conn, actor: str, action: str, target: str, detail: str, ip: str) -> None:
    await conn.execute(
        "INSERT INTO admin_audit_logs (actor, action, target, detail, ip) VALUES ($1,$2,$3,$4,$5)",
        actor, action, target, detail, ip,
    )


@router.get("/users", dependencies=[Depends(require_roles("admin"))])
async def list_users():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, username, role, display_name, is_active, created_at, last_login, created_by "
            "FROM admin_users ORDER BY created_at ASC"
        )
    return {"users": [dict(r) for r in rows]}


@router.post("/users", dependencies=[Depends(require_roles("admin"))])
async def create_user(body: CreateUserBody, request: Request):
    if body.role not in ("admin", "agent", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be admin, agent, or viewer")
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    ip = request.client.host if request.client else ""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT id FROM admin_users WHERE username = $1", body.username)
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")
        await conn.execute(
            "INSERT INTO admin_users (username, password_hash, role, display_name, created_by) "
            "VALUES ($1, $2, $3, $4, $5)",
            body.username, hash_password(body.password), body.role,
            body.display_name or body.username, actor,
        )
        await _audit(conn, actor, "user_created", body.username, body.role, ip)
    return {"ok": True, "username": body.username}


@router.patch("/users/{username}", dependencies=[Depends(require_roles("admin"))])
async def update_user(username: str, body: UpdateUserBody, request: Request):
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    ip = request.client.host if request.client else ""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM admin_users WHERE username = $1", username)
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        if body.role is not None:
            if body.role not in ("admin", "agent", "viewer"):
                raise HTTPException(status_code=400, detail="Invalid role")
            await conn.execute("UPDATE admin_users SET role = $1 WHERE username = $2", body.role, username)
        if body.display_name is not None:
            await conn.execute("UPDATE admin_users SET display_name = $1 WHERE username = $2", body.display_name, username)
        if body.is_active is not None:
            await conn.execute("UPDATE admin_users SET is_active = $1 WHERE username = $2", body.is_active, username)
            r = get_redis()
            if body.is_active is False:
                await r.sadd("auth:revoked", username)
                await r.expire("auth:revoked", settings.admin_token_ttl_seconds)
            else:
                await r.srem("auth:revoked", username)
        detail = f"role={body.role},active={body.is_active}"
        await _audit(conn, actor, "user_updated", username, detail, ip)
    return {"ok": True}


@router.post("/users/{username}/password", dependencies=[Depends(require_roles("admin"))])
async def reset_password(username: str, body: ResetPasswordBody, request: Request):
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    ip = request.client.host if request.client else ""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM admin_users WHERE username = $1", username)
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        await conn.execute(
            "UPDATE admin_users SET password_hash = $1 WHERE username = $2",
            hash_password(body.new_password), username,
        )
        await _audit(conn, actor, "password_reset", username, "", ip)
    return {"ok": True}


@router.delete("/users/{username}", dependencies=[Depends(require_roles("admin"))])
async def deactivate_user(username: str, request: Request):
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    ip = request.client.host if request.client else ""
    if actor == username:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM admin_users WHERE username = $1", username)
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        await conn.execute("UPDATE admin_users SET is_active = FALSE WHERE username = $1", username)
        r = get_redis()
        await r.sadd("auth:revoked", username)
        await r.expire("auth:revoked", settings.admin_token_ttl_seconds)
        await _audit(conn, actor, "user_deactivated", username, "", ip)
    return {"ok": True}
