from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    app_env: str = "development"
    company_name: str = "Your Company"
    agent_name: str = "NURA"
    agent_tone: str = "formal"
    primary_language: str = "Arabic"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str

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
    chroma_port: int = 8001

    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_top_k: int = 3
    unknown_answer_behavior: str = "handoff"

    # Optional local ML model layer (disabled when model files are absent)
    ml_model_path: str = "/app/ml_models/local_model.pkl"
    ml_vectorizer_path: str = "/app/ml_models/vectorizer.pkl"
    ml_confidence_threshold: float = 0.70
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

    @field_validator("admin_secret_key")
    @classmethod
    def admin_secret_key_must_be_changed(cls, v: str, info) -> str:
        if info.data.get("app_env") == "production" and v == "admin-secret-change-in-production":
            raise ValueError("ADMIN_SECRET_KEY must be changed from the default before running")
        return v

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
