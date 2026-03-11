"""PrivateRAG FastAPI 애플리케이션 진입점."""

import sys

# Windows 이벤트 루프 정책 설정 (Playwright subprocess 지원)
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 lifespan 컨텍스트."""
    # ===== Startup =====
    logger.info("PrivateRAG 시작 중...")

    # 1. DB 초기화 (테이블 생성 또는 마이그레이션)
    from app.db.session import engine
    from app.db.base import Base
    import app.models  # noqa: F401 — 모든 모델 로드
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB 초기화 완료")

    # 2. Qdrant 컬렉션 초기화
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PayloadSchemaType
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collections = [c.name for c in qdrant.get_collections().collections]
        if settings.qdrant_collection not in collections:
            qdrant.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
                on_disk_payload=True,
            )
            qdrant.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name="doc_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info("Qdrant 컬렉션 생성 완료", collection=settings.qdrant_collection)
        else:
            logger.info("Qdrant 컬렉션 이미 존재", collection=settings.qdrant_collection)
    except Exception as e:
        logger.warning("Qdrant 초기화 실패 (계속 진행)", error=str(e))

    # 3. Provider 등록
    from app.core.app_state import register_provider, set_search_provider
    from app.providers.llm.ollama_adapter import OllamaAdapter

    ollama_default_model = "qwen2.5:7b"
    ollama_provider = OllamaAdapter(
        base_url=settings.ollama_base_url,
        model_name=ollama_default_model,
    )
    register_provider(f"ollama:{ollama_default_model}", ollama_provider)

    if settings.openai_api_key:
        from app.providers.llm.openai_adapter import OpenAIAdapter
        openai_provider = OpenAIAdapter(api_key=settings.openai_api_key)
        register_provider("openai:gpt-4o-mini", openai_provider)

    if settings.anthropic_api_key:
        from app.providers.llm.anthropic_adapter import AnthropicAdapter
        anthropic_provider = AnthropicAdapter(api_key=settings.anthropic_api_key)
        register_provider("anthropic:claude-haiku-4-5-20251001", anthropic_provider)

    if settings.brave_api_key:
        from app.providers.search.brave_adapter import BraveSearchAdapter
        set_search_provider(BraveSearchAdapter(api_key=settings.brave_api_key))
        logger.info("Brave Search Provider 등록 완료")
    else:
        logger.warning("BRAVE_API_KEY 미설정 — 검색 기능 비활성화")

    logger.info("Provider 등록 완료")

    # 4. 스케줄러 시작
    from app.scheduler.scheduler import start_scheduler
    from app.scheduler.jobs import register_system_jobs, register_topic_jobs
    start_scheduler()
    register_system_jobs()
    await register_topic_jobs()
    logger.info("스케줄러 시작 완료")

    logger.info("PrivateRAG 준비 완료", debug=settings.debug)
    yield

    # ===== Shutdown =====
    from app.scheduler.scheduler import stop_scheduler
    stop_scheduler()
    await engine.dispose()
    logger.info("PrivateRAG 종료 완료")


app = FastAPI(
    title="PrivateRAG",
    description="주제 중심 자동 수집·검증·검색 RAG 시스템",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from app.api.routes import documents, models, rag, rules, topics  # noqa: E402

app.include_router(topics.router, prefix="/topics", tags=["topics"])
app.include_router(rules.router, tags=["rules"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(rag.router, prefix="/rag", tags=["rag"])
app.include_router(models.router, prefix="/models", tags=["models"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
