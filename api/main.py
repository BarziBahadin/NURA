import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from core.job_queue import run_job_worker
from core.observability import ObservabilityMiddleware
from core.session_manager import close_redis
from core.sla_monitor import run_sla_monitor
from db.postgres import close_db_pool, init_db
from routes import ai_control, analytics, auth, canned_replies, cases, handoff, health, knowledge, knowledge_gaps, message, monitor, rules, session, upload, users, voice
from routes.auth import seed_admin_user
from routes.cases import refresh_department_cache
from routes.telegram import run_telegram_poller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

# Public widget endpoints that must accept requests from any origin (embedded sites,
# local file:// testing, customer domains). Admin endpoints remain restricted to the
# CORS_ORIGINS whitelist via the inner CORSMiddleware.
_WIDGET_PATHS = (
    "/v1/topic-tree",
    "/v1/analytics/",
    "/v1/sessions",
    "/v1/message",
    "/v1/handoff/",
    "/v1/upload",
    "/v1/uploads/",
    "/widget",
    "/vendor/",
)

_WIDGET_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Session-ID, X-Customer-ID",
    "Access-Control-Max-Age": "86400",
}


class WidgetCORSMiddleware(BaseHTTPMiddleware):
    """Outermost middleware: applies open CORS to public widget endpoints so that
    the inner strict CORSMiddleware never rejects them, regardless of origin."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_widget = any(path == p.rstrip("/") or path.startswith(p) for p in _WIDGET_PATHS)

        if is_widget and request.method == "OPTIONS":
            return Response(status_code=200, headers=_WIDGET_CORS_HEADERS)

        response = await call_next(request)

        if is_widget:
            # Overwrite whatever the inner CORSMiddleware set so there is exactly one header
            response.headers["Access-Control-Allow-Origin"] = "*"

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NURA API...")
    await init_db()
    logger.info("Database initialized")
    await refresh_department_cache()
    await seed_admin_user()
    background_tasks = [
        asyncio.create_task(run_job_worker()),
        asyncio.create_task(run_sla_monitor()),
    ]
    if settings.telegram_poller_enabled:
        background_tasks.append(asyncio.create_task(run_telegram_poller()))
    yield
    for task in background_tasks:
        task.cancel()
    for task in background_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    await close_redis()
    await close_db_pool()
    logger.info("Shutting down NURA API...")


app = FastAPI(
    title="NURA API",
    description="Neural Unified Response Agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(ObservabilityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Must be added AFTER CORSMiddleware so it wraps the outside — processes requests first.
app.add_middleware(WidgetCORSMiddleware)

app.include_router(health.router,     prefix="/v1")
app.include_router(auth.router,       prefix="/v1")
app.include_router(message.router,    prefix="/v1")
app.include_router(session.router,    prefix="/v1")
app.include_router(handoff.router,    prefix="/v1")
app.include_router(knowledge.router,  prefix="/v1")
app.include_router(knowledge_gaps.router, prefix="/v1")
app.include_router(cases.router,      prefix="/v1")
app.include_router(analytics.router,  prefix="/v1")
app.include_router(users.router,      prefix="/v1")
app.include_router(upload.router,     prefix="/v1")
app.include_router(monitor.router,    prefix="/v1")
app.include_router(ai_control.router,    prefix="/v1")
app.include_router(canned_replies.router, prefix="/v1")
app.include_router(voice.router, prefix="/v1")
app.include_router(rules.router,  prefix="/v1")


@app.get("/widget.js", include_in_schema=False)
async def serve_widget():
    return FileResponse(
        "/app/frontend/widget.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/widget-loader.js", include_in_schema=False)
async def serve_widget_loader():
    return FileResponse(
        "/app/frontend/widget-loader.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/widget.html", include_in_schema=False)
async def serve_widget_test_page():
    return FileResponse(
        "/app/frontend/widget.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/vendor/livekit-client.umd.js", include_in_schema=False)
async def serve_livekit_client():
    return FileResponse(
        "/app/frontend/vendor/livekit-client.umd.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/")
async def root():
    return {
        "service": "NURA API",
        "company": settings.company_name,
        "status": "running",
        "docs": "/docs",
    }
