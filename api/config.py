from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from typing import List

_WEAK_ADMIN_PASSWORDS = {
    "",
    "admin",
    "password",
    "changeme",
    "change-me",
    "change_me",
    "admin123",
    "password123",
    "nura",
    "nuraadmin",
}


class Settings(BaseSettings):
    app_env: str = "development"
    company_name: str = "Your Company"
    agent_name: str = "NURA"
    agent_tone: str = "formal"
    primary_language: str = "Arabic"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""
    allow_admin_api_key: bool = False

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "nura_db"
    postgres_user: str = "nura_user"
    postgres_password: str

    # Keep old startup schema creation enabled until production deploys Alembic.
    db_auto_init: bool = True

    redis_host: str = "redis"
    redis_port: int = 6379

    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_top_k: int = 3
    unknown_answer_behavior: str = "handoff"

    # Optional local ML model layer (disabled when model files are absent)
    ml_model_path: str = "/app/ml_models/local_model.pkl"
    ml_vectorizer_path: str = "/app/ml_models/vectorizer.pkl"
    ml_confidence_threshold: float = 0.70
    ml_require_artifact_hashes: bool = False
    use_semantic_embeddings: bool = False
    semantic_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"

    handoff_enabled: bool = True
    handoff_triggers: str = "angry_sentiment,explicit_request,two_failures,keywords"
    escalation_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_poller_enabled: bool = True

    background_jobs_enabled: bool = True
    job_worker_enabled: bool = True
    job_max_attempts: int = 3
    job_retry_delay_seconds: float = 5.0

    # LLM cost constants (USD per 1K tokens) — update when model pricing changes
    openai_cost_input_per_1k: float = 0.00015     # gpt-4o-mini input
    openai_cost_output_per_1k: float = 0.0006     # gpt-4o-mini output
    openai_cost_embedding_per_1k: float = 0.00002  # text-embedding-3-small

    admin_secret_key: str = "admin-secret-change-in-production"
    admin_username: str = "admin"
    admin_password: str = ""
    admin_token_ttl_seconds: int = 3600 * 8

    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:8080,http://localhost:9000"
    sentry_dsn: str = ""

    @field_validator("admin_secret_key")
    @classmethod
    def admin_secret_key_must_be_changed(cls, v: str, info) -> str:
        if v == "admin-secret-change-in-production":
            raise ValueError("ADMIN_SECRET_KEY must be changed from the default value")
        return v

    @model_validator(mode="after")
    def safety_checks(self):
        if "*" in self.cors_origins_list:
            raise ValueError("CORS_ORIGINS cannot include '*' — list specific origins instead")
        if self.app_env.lower() == "production":
            if len(self.admin_secret_key.strip()) < 32:
                raise ValueError("ADMIN_SECRET_KEY must be at least 32 characters in production")
            if not self.ml_require_artifact_hashes:
                raise ValueError("ML_REQUIRE_ARTIFACT_HASHES must be true in production")
            password = self.admin_password.strip()
            if len(password) < 12:
                raise ValueError("ADMIN_PASSWORD must be at least 12 characters in production")
            if password.lower() in _WEAK_ADMIN_PASSWORDS:
                raise ValueError("ADMIN_PASSWORD is too weak for production")
            if password == self.admin_username or password.lower() == self.admin_username.lower():
                raise ValueError("ADMIN_PASSWORD cannot match ADMIN_USERNAME in production")
            if self.allow_admin_api_key and len(self.api_key) < 32:
                raise ValueError("API_KEY must be at least 32 characters when ALLOW_ADMIN_API_KEY=true")
            localhost_origins = [o for o in self.cors_origins_list if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                raise ValueError(
                    f"CORS_ORIGINS contains localhost entries in production: {localhost_origins}. "
                    "Remove them and set real domain origins only."
                )
            if not self.sentry_dsn:
                import logging
                logging.getLogger(__name__).warning("SENTRY_DSN is not set — errors will not be reported to Sentry")
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def handoff_triggers_list(self) -> List[str]:
        return [t.strip() for t in self.handoff_triggers.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
