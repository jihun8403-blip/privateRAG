"""PrivateRAG FastAPI 애플리케이션 진입점."""

import sys

# Windows 이벤트 루프 정책 설정 (Playwright subprocess 지원)
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # 터미널 한글 깨짐 방지 (CP949 → UTF-8)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
    from sqlalchemy import text
    import app.models  # noqa: F401 — 모든 모델 로드
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # api_key 컬럼 마이그레이션 (기존 DB 호환)
        try:
            await conn.execute(text("ALTER TABLE model_registry ADD COLUMN api_key VARCHAR(500)"))
        except Exception:
            pass  # 이미 존재하는 경우 무시
        try:
            await conn.execute(text("ALTER TABLE model_registry ADD COLUMN call_interval_seconds REAL DEFAULT 0.0"))
        except Exception:
            pass  # 이미 존재하는 경우 무시
    # capability_tags 마이그레이션: relevance_check 없는 활성 모델에 추가
    from app.db.session import AsyncSessionLocal as _ASL
    from app.models.model_registry import ModelRegistry as _MR2
    from sqlalchemy import select as _sel2
    async with _ASL() as _ms:
        _mr = await _ms.execute(_sel2(_MR2).where(_MR2.enabled == True))
        for _m2 in _mr.scalars():
            tags = _m2.capability_tags or []
            if "relevance_check" not in tags and tags:
                _m2.capability_tags = tags + ["relevance_check"]
                _ms.add(_m2)
                logger.info("relevance_check capability 추가", model=_m2.model_name)
        await _ms.commit()
    logger.info("DB 초기화 완료")

    # 2. Qdrant 컬렉션 초기화
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, prefer_grpc=False)
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
                field_schema="keyword",
            )
            logger.info("Qdrant 컬렉션 생성 완료", collection=settings.qdrant_collection)
        else:
            logger.info("Qdrant 컬렉션 이미 존재", collection=settings.qdrant_collection)
    except Exception as e:
        logger.warning("Qdrant 초기화 실패 (계속 진행)", error=str(e))

    # 3. Provider 등록
    from app.core.app_state import register_provider, set_search_provider, get_providers
    from app.providers.llm.ollama_adapter import OllamaAdapter

    # env 기반 기본 provider 등록
    if settings.openai_api_key:
        from app.providers.llm.openai_adapter import OpenAIAdapter
        register_provider("openai:gpt-4o-mini", OpenAIAdapter(api_key=settings.openai_api_key))

    if settings.anthropic_api_key:
        from app.providers.llm.anthropic_adapter import AnthropicAdapter
        register_provider("anthropic:claude-haiku-4-5-20251001", AnthropicAdapter(api_key=settings.anthropic_api_key))

    # DB에 등록된 활성 모델을 전부 provider로 등록 (model_name 자유)
    from app.db.session import AsyncSessionLocal
    from app.models.model_registry import ModelRegistry as _ModelRegistry
    from sqlalchemy import select as _sa_select
    async with AsyncSessionLocal() as _session:
        _result = await _session.execute(
            _sa_select(_ModelRegistry).where(_ModelRegistry.enabled == True)
        )
        for _m in _result.scalars():
            _key = f"{_m.provider}:{_m.model_name}"
            if _key in get_providers():
                continue
            try:
                if _m.provider == "ollama":
                    register_provider(_key, OllamaAdapter(
                        base_url=settings.ollama_base_url,
                        model_name=_m.model_name,
                    ))
                elif _m.provider == "openai" and _m.api_key:
                    from app.providers.llm.openai_adapter import OpenAIAdapter
                    register_provider(_key, OpenAIAdapter(api_key=_m.api_key, model_name=_m.model_name))
                elif _m.provider == "anthropic" and _m.api_key:
                    from app.providers.llm.anthropic_adapter import AnthropicAdapter
                    register_provider(_key, AnthropicAdapter(api_key=_m.api_key, model_name=_m.model_name))
                elif _m.provider in ("google", "gemini"):
                    _api_key = _m.api_key or settings.gemini_api_key
                    if _api_key:
                        from app.providers.llm.google_adapter import GoogleAdapter
                        register_provider(_key, GoogleAdapter(api_key=_api_key, model_name=_m.model_name))
            except Exception as e:
                logger.warning("Provider 등록 실패 (스킵)", key=_key, error=str(e))

    if settings.brave_api_key:
        from app.providers.search.brave_adapter import BraveSearchAdapter
        set_search_provider(BraveSearchAdapter(api_key=settings.brave_api_key))
        logger.info("Brave Search Provider 등록 완료")
    else:
        logger.warning("BRAVE_API_KEY 미설정 — 검색 기능 비활성화")

    logger.info("Provider 등록 완료", registered=list(get_providers().keys()))

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
