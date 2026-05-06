import logging
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("nura.requests")

REQUEST_COUNTER: Counter[str] = Counter()
REQUEST_LATENCY_MS: Counter[str] = Counter()
EVENT_COUNTER: Counter[str] = Counter()
EVENT_VALUES: Counter[str] = Counter()
LAST_EVENTS: dict[str, str] = {}


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                "request_failed request_id=%s method=%s path=%s elapsed_ms=%s",
                request_id,
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        key = f"{request.method} {request.url.path} {response.status_code}"
        REQUEST_COUNTER[key] += 1
        REQUEST_LATENCY_MS[key] += elapsed_ms
        response.headers["X-Request-ID"] = request_id

        if elapsed_ms >= 1000:
            logger.warning(
                "slow_request request_id=%s method=%s path=%s status=%s elapsed_ms=%s",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        else:
            logger.info(
                "request request_id=%s method=%s path=%s status=%s elapsed_ms=%s",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        return response


def metrics_snapshot() -> dict:
    return {
        "requests": dict(REQUEST_COUNTER),
        "total_latency_ms": dict(REQUEST_LATENCY_MS),
        "events": dict(EVENT_COUNTER),
        "event_values": dict(EVENT_VALUES),
        "last_events": dict(LAST_EVENTS),
    }


def record_event(name: str, value: int = 1, **labels: Any) -> None:
    label = _metric_key(name, labels)
    EVENT_COUNTER[label] += 1
    EVENT_VALUES[label] += int(value or 0)
    LAST_EVENTS[label] = datetime.now(timezone.utc).isoformat()


def record_failure(name: str, **labels: Any) -> None:
    record_event(f"{name}.failed", **labels)


def _metric_key(name: str, labels: dict[str, Any]) -> str:
    clean = {k: str(v) for k, v in labels.items() if v is not None and v != ""}
    if not clean:
        return name
    suffix = ",".join(f"{k}={clean[k]}" for k in sorted(clean))
    return f"{name}|{suffix}"
