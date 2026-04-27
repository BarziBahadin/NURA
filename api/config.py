from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
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

    # LLM cost constants (USD per 1K tokens) — update when model pricing changes
    openai_cost_input_per_1k: float = 0.00015     # gpt-4o-mini input
    openai_cost_output_per_1k: float = 0.0006     # gpt-4o-mini output
    openai_cost_embedding_per_1k: float = 0.00002  # text-embedding-3-small

    admin_secret_key: str = "admin-secret-change-in-production"

    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:8080,http://localhost:9000"

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
