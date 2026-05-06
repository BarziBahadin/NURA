import asyncio
import json
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from openai import AsyncOpenAI

from config import settings
from core.auth import verify_api_key
from core.observability import metrics_snapshot

router = APIRouter()

_openai_client: Optional[AsyncOpenAI] = None
_openai_lock = asyncio.Lock()
_health_cache: dict = {}
_HEALTH_TTL = 60


async def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    async with _openai_lock:
        if _openai_client is None:
            _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def _check_openai() -> str:
    try:
        client = await _get_openai_client()
        await client.models.list()
        return "ok"
    except Exception:
        return "error"


async def _check_redis() -> str:
    try:
        from core.session_manager import get_redis
        await get_redis().ping()
        return "ok"
    except Exception:
        return "error"


async def _check_chromadb() -> str:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat"
            )
            return "ok" if r.status_code == 200 else "error"
    except Exception:
        return "error"


async def _check_postgres() -> str:
    try:
        from db.postgres import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return "ok"
    except Exception:
        return "error"


@router.get("/health")
async def health_check(_: None = Depends(verify_api_key)):
    now = time.monotonic()
    if _health_cache.get("at", 0) and (now - _health_cache["at"]) < _HEALTH_TTL:
        return _health_cache["result"]

    openai_status, redis_status, chroma_status, pg_status = await asyncio.gather(
        _check_openai(),
        _check_redis(),
        _check_chromadb(),
        _check_postgres(),
    )

    services = {
        "api":      "ok",
        "openai":   openai_status,
        "redis":    redis_status,
        "chromadb": chroma_status,
        "postgres": pg_status,
    }
    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    result = {"status": overall, "services": services}
    _health_cache["result"] = result
    _health_cache["at"] = now
    return result


@router.get("/metrics")
async def metrics(_: None = Depends(verify_api_key)):
    return metrics_snapshot()


_topic_tree_cache: Optional[dict] = None


@router.get("/topic-tree")
async def get_topic_tree():
    global _topic_tree_cache
    if _topic_tree_cache is not None:
        return _topic_tree_cache
    with open("/app/manafest/topic_tree.json", "r", encoding="utf-8") as f:
        _topic_tree_cache = json.load(f)
    return _topic_tree_cache
