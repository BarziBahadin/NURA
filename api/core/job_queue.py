import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from config import settings
from core.session_manager import get_redis
from core.utils import fire_task

logger = logging.getLogger(__name__)

JOB_QUEUE_KEY = "nura:jobs:queue"
JOB_PROCESSING_KEY = "nura:jobs:processing"
JOB_FAILED_KEY = "nura:jobs:failed"

JOB_INTENT_CLASSIFICATION = "intent_classification"
JOB_ESCALATION_WEBHOOK = "escalation_webhook"


async def enqueue_job(job_type: str, **payload: Any) -> str:
    job = {
        "id": str(uuid.uuid4()),
        "type": job_type,
        "payload": payload,
        "attempts": 0,
        "max_attempts": settings.job_max_attempts,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }

    if not settings.background_jobs_enabled:
        fire_task(process_job(job), label=f"job:{job_type}")
        return job["id"]

    try:
        await get_redis().lpush(JOB_QUEUE_KEY, json.dumps(job))
    except Exception as e:
        logger.error(f"Failed to enqueue job {job_type}: {e}")
        fire_task(process_job(job), label=f"job:{job_type}")
    return job["id"]


async def run_job_worker(worker_name: str = "api-worker") -> None:
    if not settings.background_jobs_enabled or not settings.job_worker_enabled:
        logger.info("Background job worker disabled")
        return

    logger.info(f"Background job worker started: {worker_name}")
    r = get_redis()

    while True:
        raw = None
        try:
            raw = await r.brpoplpush(JOB_QUEUE_KEY, JOB_PROCESSING_KEY, timeout=1)
            if not raw:
                await asyncio.sleep(0)
                continue

            job = json.loads(raw)
            await process_job(job)
            await r.lrem(JOB_PROCESSING_KEY, 1, raw)
        except asyncio.CancelledError:
            logger.info(f"Background job worker cancelled: {worker_name}")
            raise
        except Exception as e:
            logger.exception(f"Background job worker error: {e}")
            if raw:
                await _handle_failed_raw_job(raw)
            await asyncio.sleep(1)


async def _handle_failed_raw_job(raw: str) -> None:
    r = get_redis()
    try:
        job = json.loads(raw)
    except Exception:
        await r.lpush(JOB_FAILED_KEY, raw)
        await r.lrem(JOB_PROCESSING_KEY, 1, raw)
        return

    job["attempts"] = int(job.get("attempts", 0)) + 1
    job["last_error_at"] = datetime.now(timezone.utc).isoformat()
    updated = json.dumps(job)

    await r.lrem(JOB_PROCESSING_KEY, 1, raw)
    if job["attempts"] < int(job.get("max_attempts", settings.job_max_attempts)):
        await asyncio.sleep(settings.job_retry_delay_seconds)
        await r.lpush(JOB_QUEUE_KEY, updated)
    else:
        await r.lpush(JOB_FAILED_KEY, updated)
        logger.error(f"Job failed permanently: {job.get('type')} id={job.get('id')}")


async def process_job(job: dict[str, Any]) -> None:
    job_type = job.get("type")
    payload = job.get("payload") or {}

    if job_type == JOB_INTENT_CLASSIFICATION:
        from core.intent_classifier import classify_and_log_message

        await classify_and_log_message(**payload)
        return

    if job_type == JOB_ESCALATION_WEBHOOK:
        await send_escalation_webhook(**payload)
        return

    raise ValueError(f"Unknown job type: {job_type}")


async def send_escalation_webhook(
    session_id: str,
    customer_id: str,
    channel: str,
    trigger_message: str,
) -> None:
    url = settings.escalation_webhook_url
    if not url:
        return

    payload = {
        "event": "escalation",
        "session_id": session_id,
        "customer_id": customer_id,
        "channel": channel,
        "trigger_message": trigger_message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
