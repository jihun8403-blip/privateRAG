"""pytest 공통 픽스처 (TS §5.2, TCC 기반)."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — 모든 모델 등록
from app.db.base import Base
from app.models.model_registry import ModelRegistry
from app.models.topic import Topic, TopicRule
from app.providers.llm.base import BaseLLMProvider, LLMResponse


# ===== DB 픽스처 =====

@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """각 테스트마다 새로운 in-memory SQLite DB (TS §5.1)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


# ===== 주제 픽스처 =====

@pytest.fixture
def sample_topic() -> Topic:
    """TC-T01 기준 샘플 주제 (TS §5.2)."""
    return Topic(
        topic_id="t001",
        name="로컬 LLM 에이전트",
        description="온프레미스 LLM 에이전트 프레임워크 추적",
        language="ko,en",
        priority=8,
        enabled=True,
        schedule_cron="0 */6 * * *",
        relevance_threshold=0.6,
        must_include=["local llm", "agent"],
        must_exclude=["openai exclusive"],
    )


@pytest.fixture
def sample_topic_with_rules(sample_topic) -> Topic:
    """도메인 룰이 있는 주제."""
    sample_topic.rules = [
        TopicRule(
            rule_id="r001",
            topic_id="t001",
            rule_type="preferred_domain",
            pattern=r"github\.com",
            is_regex=True,
            enabled=True,
            priority=0,
        ),
        TopicRule(
            rule_id="r002",
            topic_id="t001",
            rule_type="blocked_domain",
            pattern=r"pinterest\.com",
            is_regex=True,
            enabled=True,
            priority=0,
        ),
    ]
    return sample_topic


# ===== Mock LLM 픽스처 =====

@pytest.fixture
def mock_llm_provider(mocker) -> BaseLLMProvider:
    """LLMResponse를 고정 반환하는 Mock Provider (TS §3.1)."""
    provider = mocker.AsyncMock(spec=BaseLLMProvider)
    provider.complete.return_value = LLMResponse(
        content='{"queries": [{"query": "local llm agent framework", "intent": "broad", "language": "en"}, {"query": "로컬 LLM 에이전트", "intent": "broad", "language": "ko"}]}',
        model_name="mock-model",
        input_tokens=100,
        output_tokens=50,
        duration_ms=100,
    )
    provider.health_check.return_value = True
    return provider


@pytest.fixture
def mock_relevance_provider(mocker) -> BaseLLMProvider:
    """관련성 검증 고득점 반환 Mock."""
    provider = mocker.AsyncMock(spec=BaseLLMProvider)
    provider.complete.return_value = LLMResponse(
        content='{"is_relevant": true, "score": 0.87, "reason": "주제와 매우 관련됨"}',
        model_name="mock-model",
        input_tokens=80,
        output_tokens=30,
        duration_ms=80,
    )
    provider.health_check.return_value = True
    return provider


@pytest.fixture
def mock_low_relevance_provider(mocker) -> BaseLLMProvider:
    """관련성 검증 저득점 반환 Mock (TC-V04)."""
    provider = mocker.AsyncMock(spec=BaseLLMProvider)
    provider.complete.return_value = LLMResponse(
        content='{"is_relevant": false, "score": 0.3, "reason": "주제와 무관함"}',
        model_name="mock-model",
        input_tokens=80,
        output_tokens=30,
        duration_ms=80,
    )
    provider.health_check.return_value = True
    return provider


# ===== ModelRegistry 픽스처 =====

@pytest_asyncio.fixture
async def sample_model_a(db_session: AsyncSession) -> ModelRegistry:
    """capability=query_gen, 예산 여유 있는 모델."""
    model = ModelRegistry(
        model_id="m001",
        provider="ollama",
        model_name="qwen2.5:7b",
        capability_tags=["query_gen", "relevance_check", "answer"],
        daily_budget_tokens=10000,
        used_tokens_today=0,
        priority=1,
        fallback_order=1,
        enabled=True,
    )
    db_session.add(model)
    await db_session.flush()
    return model


@pytest_asyncio.fixture
async def sample_model_b(db_session: AsyncSession) -> ModelRegistry:
    """capability=relevance_check, fallback 모델."""
    model = ModelRegistry(
        model_id="m002",
        provider="ollama",
        model_name="llama3.2:3b",
        capability_tags=["relevance_check", "answer"],
        daily_budget_tokens=5000,
        used_tokens_today=0,
        priority=2,
        fallback_order=2,
        enabled=True,
    )
    db_session.add(model)
    await db_session.flush()
    return model
