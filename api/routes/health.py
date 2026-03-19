import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter

from config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    services = {
        "api": "ok",
        "ollama": "unknown",
        "redis": "unknown",
        "chromadb": "unknown",
        "postgres": "unknown",
    }

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.ollama_host}/api/tags")
            services["ollama"] = "ok" if r.status_code == 200 else "error"
    except Exception:
        services["ollama"] = "error"

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
    return {"status": overall, "services": services}
