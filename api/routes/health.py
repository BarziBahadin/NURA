import time
import httpx
import redis.asyncio as aioredis
from openai import AsyncOpenAI
from fastapi import APIRouter, Depends
from typing import Optional

from core.auth import verify_api_key
from config import settings

router = APIRouter()

_openai_client: Optional[AsyncOpenAI] = None
_health_cache: dict = {}
_HEALTH_TTL = 60  # seconds — avoids hammering OpenAI/Chroma on every dashboard refresh


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


@router.get("/health")
async def health_check(_: None = Depends(verify_api_key)):
    now = time.monotonic()
    if _health_cache.get("at", 0) and (now - _health_cache["at"]) < _HEALTH_TTL:
        return _health_cache["result"]

    services = {
        "api": "ok",
        "openai": "unknown",
        "redis": "unknown",
        "chromadb": "unknown",
        "postgres": "unknown",
    }

    # OpenAI
    try:
        client = get_openai_client()
        await client.models.list()
        services["openai"] = "ok"
    except Exception:
        services["openai"] = "error"

    # Redis
    try:
        r = aioredis.Redis(host=settings.redis_host, port=settings.redis_port)
        await r.ping()
        await r.aclose()
        services["redis"] = "ok"
    except Exception:
        services["redis"] = "error"

    # ChromaDB
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat"
            )
            services["chromadb"] = "ok" if r.status_code == 200 else "error"
    except Exception:
        services["chromadb"] = "error"

    # Postgres
    try:
        from db.postgres import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        services["postgres"] = "ok"
    except Exception:
        services["postgres"] = "error"

    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    result = {"status": overall, "services": services}
    _health_cache["result"] = result
    _health_cache["at"] = now
    return result
