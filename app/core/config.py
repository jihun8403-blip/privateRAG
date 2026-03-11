"""애플리케이션 설정 관리.

pydantic-settings 기반으로 .env 파일과 config/settings.yaml을 함께 로드합니다.
환경변수가 YAML 파일 설정보다 우선합니다.
"""

from pathlib import Path
from typing import Optional

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # === 데이터베이스 ===
    database_url: str = "sqlite+aiosqlite:///./data/privaterag.db"

    # === Qdrant ===
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "privaterag"

    # === Ollama ===
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_timeout: int = 120

    # === LLM Provider API 키 ===
    brave_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # === 저장소 경로 ===
    storage_raw_base: str = "data/raw"
    storage_normalized_base: str = "data/normalized"
    storage_archive_base: str = "data/archive"

    # === 임베딩 ===
    embedding_model: str = "paraphrase-multilingual-mpnet-base-v2"
    embedding_dimension: int = 768
    embedding_batch_size: int = 32

    # === 관련성 검증 ===
    relevance_default_threshold: float = 0.6
    relevance_min_text_length: int = 200

    # === 청킹 ===
    chunking_chunk_size: int = 400
    chunking_chunk_overlap: int = 50

    # === 아카이브 ===
    archive_warm_after_days: int = 90
    archive_cold_after_days: int = 365

    # === 검색 수집 ===
    search_default_count: int = 10
    search_max_concurrent_fetches: int = 5
    search_domain_delay_seconds: float = 1.0

    # === 스케줄러 ===
    scheduler_timezone: str = "Asia/Seoul"

    # === 앱 전반 ===
    debug: bool = False
    log_level: str = "INFO"

    @field_validator("storage_raw_base", "storage_normalized_base", "storage_archive_base", mode="before")
    @classmethod
    def ensure_directories(cls, v: str) -> str:
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def sync_database_url(self) -> str:
        """APScheduler 등 동기 SQLAlchemy용 URL (aiosqlite 제거)."""
        return self.database_url.replace("+aiosqlite", "")

    @property
    def raw_base_path(self) -> Path:
        return Path(self.storage_raw_base)

    @property
    def normalized_base_path(self) -> Path:
        return Path(self.storage_normalized_base)

    @property
    def archive_base_path(self) -> Path:
        return Path(self.storage_archive_base)


# 싱글톤 설정 인스턴스
settings = Settings()
