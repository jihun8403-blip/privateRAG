"""Topics API 테스트 (TC-API01~TC-API03)."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db


@pytest.fixture
async def test_app():
    """테스트용 FastAPI 앱 (DB 오버라이드 포함)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # 라우터만 테스트 (lifespan 제외)
    from fastapi import FastAPI
    from app.api.routes import topics, rules, documents, models, rag

    test_app = FastAPI()
    test_app.include_router(topics.router, prefix="/topics")
    test_app.include_router(rules.router)
    test_app.include_router(documents.router, prefix="/documents")
    test_app.include_router(models.router, prefix="/models")

    test_app.dependency_overrides[get_db] = override_get_db

    yield test_app

    await engine.dispose()


@pytest.fixture
async def client(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as c:
        yield c


class TestTopicsApi:
    async def test_create_topic_success(self, client):
        """주제 정상 생성 — 201 반환."""
        payload = {
            "name": "로컬 LLM 에이전트",
            "description": "온프레미스 LLM 에이전트 추적",
            "priority": 8,
            "enabled": True,
            "schedule_cron": "0 */6 * * *",
            "relevance_threshold": 0.6,
            "must_include": ["local llm"],
            "must_exclude": [],
        }
        response = await client.post("/topics", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "로컬 LLM 에이전트"
        assert "topic_id" in data

    async def test_create_topic_missing_required_fields(self, client):
        """TC-API01: 필수 필드 누락 시 422 반환."""
        response = await client.post("/topics", json={})
        assert response.status_code == 422

    async def test_create_topic_invalid_cron(self, client):
        """TC-API02: 잘못된 cron 표현식 시 422 반환."""
        payload = {
            "name": "Test",
            "description": "테스트",
            "schedule_cron": "invalid",
        }
        response = await client.post("/topics", json=payload)
        assert response.status_code == 422

    async def test_get_nonexistent_topic(self, client):
        """TC-API03: 존재하지 않는 주제 조회 시 404."""
        response = await client.get("/topics/nonexistent_id")
        assert response.status_code == 404

    async def test_list_topics_empty(self, client):
        """주제 없을 때 빈 목록 반환."""
        response = await client.get("/topics")
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_and_get_topic(self, client):
        """주제 생성 후 단건 조회."""
        payload = {
            "name": "테스트 주제",
            "description": "단위 테스트용",
            "schedule_cron": "0 9 * * *",
        }
        create_resp = await client.post("/topics", json=payload)
        assert create_resp.status_code == 201
        topic_id = create_resp.json()["topic_id"]

        get_resp = await client.get(f"/topics/{topic_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "테스트 주제"

    async def test_delete_topic(self, client):
        """주제 삭제 후 404 반환."""
        payload = {
            "name": "삭제할 주제",
            "description": "삭제 테스트",
            "schedule_cron": "0 9 * * *",
        }
        create_resp = await client.post("/topics", json=payload)
        topic_id = create_resp.json()["topic_id"]

        delete_resp = await client.delete(f"/topics/{topic_id}")
        assert delete_resp.status_code == 204

        get_resp = await client.get(f"/topics/{topic_id}")
        assert get_resp.status_code == 404
