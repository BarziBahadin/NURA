from fastapi import APIRouter, Depends, Request

from core.auth import get_admin_identity, require_roles
from core.session_manager import get_redis
from db.postgres import get_db_pool

router = APIRouter()

OPENAI_FLAG_KEY = "ai:enabled"


async def is_openai_enabled() -> bool:
    r = get_redis()
    val = await r.get(OPENAI_FLAG_KEY)
    return val != "0"


async def is_ai_enabled() -> bool:
    return await is_openai_enabled()


@router.get("/ai/status")
async def ai_status(_: None = Depends(require_roles("admin", "agent"))):
    enabled = await is_openai_enabled()
    return {"ai_enabled": enabled, "openai_enabled": enabled}


@router.post("/ai/enable", dependencies=[Depends(require_roles("admin"))])
async def enable_ai(request: Request):
    r = get_redis()
    await r.set(OPENAI_FLAG_KEY, "1")
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    ip = request.client.host if request.client else ""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO admin_audit_logs (actor, action, target, detail, ip) VALUES ($1,$2,$3,$4,$5)",
            actor, "openai_enabled", "openai", "", ip,
        )
    return {"ai_enabled": True, "openai_enabled": True}


@router.post("/ai/disable", dependencies=[Depends(require_roles("admin"))])
async def disable_ai(request: Request):
    r = get_redis()
    await r.set(OPENAI_FLAG_KEY, "0")
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    ip = request.client.host if request.client else ""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO admin_audit_logs (actor, action, target, detail, ip) VALUES ($1,$2,$3,$4,$5)",
            actor, "openai_disabled", "openai", "", ip,
        )
    return {"ai_enabled": False, "openai_enabled": False}
