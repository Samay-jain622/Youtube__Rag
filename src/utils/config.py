"""Centralized environment-based application settings."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    qdrant_url: str | None = os.getenv("QDRANT_URL")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:9999")
    llm_model: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://youtube:youtube@localhost:5433/youtube_rag",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url: str = os.getenv(
        "CELERY_BROKER_URL", "redis://localhost:6379/1"
    )
    qdrant_collection: str = os.getenv(
        "QDRANT_COLLECTION", "youtube_transcripts"
    )
    embedding_size: int = int(os.getenv("EMBEDDING_SIZE", "1536"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    max_video_duration_seconds: int = int(
        os.getenv("MAX_VIDEO_DURATION_SECONDS", "14400")
    )
    backend_workers: int = int(os.getenv("BACKEND_WORKERS", "1"))
    api_access_key: str | None = os.getenv("API_ACCESS_KEY")

    @property
    def knowledge_base_dir(self) -> Path:
        return self.data_dir / "knowledge_base"


settings = Settings()
settings.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
