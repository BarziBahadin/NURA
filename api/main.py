import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from core.job_queue import run_job_worker
from core.observability import ObservabilityMiddleware
from db.postgres import init_db
from routes import ai_control, analytics, auth, handoff, health, knowledge, knowledge_gaps, message, monitor, session, upload, users
from routes.auth import seed_admin_user
from routes.telegram import run_telegram_poller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NURA API...")
    await init_db()
    logger.info("Database initialized")
    await seed_admin_user()
    background_tasks = [asyncio.create_task(run_job_worker())]
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

app.include_router(health.router,     prefix="/v1")
app.include_router(auth.router,       prefix="/v1")
app.include_router(message.router,    prefix="/v1")
app.include_router(session.router,    prefix="/v1")
app.include_router(handoff.router,    prefix="/v1")
app.include_router(knowledge.router,  prefix="/v1")
app.include_router(knowledge_gaps.router, prefix="/v1")
app.include_router(analytics.router,  prefix="/v1")
app.include_router(users.router,      prefix="/v1")
app.include_router(upload.router,     prefix="/v1")
app.include_router(monitor.router,    prefix="/v1")
app.include_router(ai_control.router, prefix="/v1")


@app.get("/widget.js", include_in_schema=False)
async def serve_widget():
    return FileResponse("/app/frontend/widget.js", media_type="application/javascript")


@app.get("/")
async def root():
    return {
        "service": "NURA API",
        "company": settings.company_name,
        "status": "running",
        "docs": "/docs",
    }
