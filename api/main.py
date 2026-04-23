import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from db.postgres import init_db
from routes import analytics, handoff, health, knowledge, message, session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NURA API...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down NURA API...")


app = FastAPI(
    title="NURA API",
    description="Neural Unified Response Agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router,     prefix="/v1")
app.include_router(message.router,    prefix="/v1")
app.include_router(session.router,    prefix="/v1")
app.include_router(handoff.router,    prefix="/v1")
app.include_router(knowledge.router,  prefix="/v1")
app.include_router(analytics.router,  prefix="/v1")


@app.get("/")
async def root():
    return {
        "service": "NURA API",
        "company": settings.company_name,
        "status": "running",
        "docs": "/docs",
    }
