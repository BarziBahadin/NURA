import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from config import settings
from core.observability import record_event, record_failure
from core.session_manager import get_redis
from core.utils import fire_task

logger = logging.getLogger(__name__)

JOB_QUEUE_KEY = "nura:jobs:queue"
JOB_PROCESSING_KEY = "nura:jobs:processing"
JOB_FAILED_KEY = "nura:jobs:failed"
JOB_STALE_SECONDS = 15 * 60
JOB_RECOVERY_INTERVAL_SECONDS = 60

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
    last_recovery_at = 0.0

    while True:
        raw = None
        try:
            await r.setex(f"health:job_worker:{worker_name}", 90, datetime.now(timezone.utc).isoformat())
            if time.monotonic() - last_recovery_at >= JOB_RECOVERY_INTERVAL_SECONDS:
                await recover_stale_jobs()
                last_recovery_at = time.monotonic()

            raw = await r.blmove(JOB_QUEUE_KEY, JOB_PROCESSING_KEY, timeout=1, src="RIGHT", dest="LEFT")
            if not raw:
                await asyncio.sleep(0)
                continue

            raw = await _mark_raw_job_processing(r, raw, worker_name)
            job = json.loads(raw)
            await process_job(job)
            record_event("jobs.completed", type=job.get("type"))
            await r.lrem(JOB_PROCESSING_KEY, 1, raw)
        except asyncio.CancelledError:
            logger.info(f"Background job worker cancelled: {worker_name}")
            raise
        except Exception as e:
            logger.exception(f"Background job worker error: {e}")
            record_failure("jobs")
            if raw:
                await _handle_failed_raw_job(raw)
            await asyncio.sleep(1)


async def recover_stale_jobs(
    *,
    stale_after_seconds: int = JOB_STALE_SECONDS,
    now: datetime | None = None,
) -> int:
    """Requeue jobs abandoned in the processing list after a worker crash."""
    r = get_redis()
    now = now or datetime.now(timezone.utc)
    recovered = 0

    for raw in await r.lrange(JOB_PROCESSING_KEY, 0, -1):
        raw_text = _decode_raw_job(raw)
        try:
            job = json.loads(raw_text)
        except Exception:
            logger.warning("Skipping malformed job in processing list")
            continue

        started_at = _parse_job_datetime(job.get("processing_started_at"))
        if not started_at:
            job["processing_started_at"] = now.isoformat()
            job.setdefault("processing_worker", "unknown")
            await _replace_processing_raw(r, raw, json.dumps(job))
            continue

        if (now - started_at).total_seconds() < stale_after_seconds:
            continue

        await r.lrem(JOB_PROCESSING_KEY, 1, raw)
        job["attempts"] = int(job.get("attempts", 0)) + 1
        job["last_requeued_at"] = now.isoformat()
        job.pop("processing_started_at", None)
        job.pop("processing_worker", None)
        updated = json.dumps(job)

        if job["attempts"] < int(job.get("max_attempts", settings.job_max_attempts)):
            await r.lpush(JOB_QUEUE_KEY, updated)
            logger.warning(f"Requeued stale job: {job.get('type')} id={job.get('id')}")
        else:
            await r.lpush(JOB_FAILED_KEY, updated)
            logger.error(f"Stale job failed permanently: {job.get('type')} id={job.get('id')}")
        recovered += 1

    return recovered


async def _mark_raw_job_processing(r: Any, raw: Any, worker_name: str) -> str:
    raw_text = _decode_raw_job(raw)
    try:
        job = json.loads(raw_text)
    except Exception:
        return raw_text

    job["processing_started_at"] = datetime.now(timezone.utc).isoformat()
    job["processing_worker"] = worker_name
    updated = json.dumps(job)
    await _replace_processing_raw(r, raw, updated)
    return updated


async def _handle_failed_raw_job(raw: str) -> None:
    r = get_redis()
    raw_text = _decode_raw_job(raw)
    try:
        job = json.loads(raw_text)
    except Exception:
        await r.lpush(JOB_FAILED_KEY, raw)
        await r.lrem(JOB_PROCESSING_KEY, 1, raw)
        return

    job["attempts"] = int(job.get("attempts", 0)) + 1
    job["last_error_at"] = datetime.now(timezone.utc).isoformat()
    job.pop("processing_started_at", None)
    job.pop("processing_worker", None)
    updated = json.dumps(job)

    await r.lrem(JOB_PROCESSING_KEY, 1, raw)
    if job["attempts"] < int(job.get("max_attempts", settings.job_max_attempts)):
        await asyncio.sleep(settings.job_retry_delay_seconds)
        await r.lpush(JOB_QUEUE_KEY, updated)
    else:
        await r.lpush(JOB_FAILED_KEY, updated)
        logger.error(f"Job failed permanently: {job.get('type')} id={job.get('id')}")


async def _replace_processing_raw(r: Any, old_raw: Any, new_raw: str) -> None:
    removed = await r.lrem(JOB_PROCESSING_KEY, 1, old_raw)
    if removed:
        await r.lpush(JOB_PROCESSING_KEY, new_raw)


def _decode_raw_job(raw: Any) -> str:
    if isinstance(raw, bytes):
        return raw.decode("utf-8")
    return str(raw)


def _parse_job_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


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
