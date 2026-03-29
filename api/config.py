from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    company_name: str = "Your Company"
    agent_name: str = "NURA"
    agent_tone: str = "formal"
    primary_language: str = "Arabic"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "nura-dev-key-change-in-production"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "nura_db"
    postgres_user: str = "nura_user"
    postgres_password: str = "NuraSecure2024!"

    redis_host: str = "redis"
    redis_port: int = 6379

    chroma_host: str = "chromadb"
    chroma_port: int = 8001

    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_top_k: int = 3
    unknown_answer_behavior: str = "handoff"

    handoff_enabled: bool = True
    handoff_triggers: str = "angry_sentiment,explicit_request,two_failures,keywords"

    channel_web_widget: bool = True

    admin_enabled: bool = True
    admin_port: int = 3000
    admin_secret_key: str = "admin-secret-change-in-production"

    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def handoff_triggers_list(self) -> List[str]:
        return [t.strip() for t in self.handoff_triggers.split(",")]

    @property
    def postgres_async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
