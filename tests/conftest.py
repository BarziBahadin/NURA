import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("POSTGRES_PASSWORD", "test-postgres-password")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def build_app():
    def _build_app(*routers):
        from core.auth import verify_api_key

        app = FastAPI()
        app.state.limiter = Limiter(key_func=get_remote_address)
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.dependency_overrides[verify_api_key] = lambda: None
        for router in routers:
            app.include_router(router, prefix="/v1")
        return app

    return _build_app
