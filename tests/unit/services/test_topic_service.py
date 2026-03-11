"""Topic Service 단위 테스트 (TC-T01~T04)."""

import pytest

from app.api.schemas.topic import TopicCreate, TopicRuleCreate, TopicUpdate
from app.services.topic_service import TopicService


class TestTopicService:
    async def test_create_topic(self, db_session):
        """TC-T01: 주제 정상 생성 — DB에 레코드 삽입 및 ID 반환."""
        svc = TopicService(db_session)
        data = TopicCreate(
            name="로컬 LLM 에이전트",
            description="온프레미스 LLM 에이전트 프레임워크 추적",
            priority=8,
            enabled=True,
            schedule_cron="0 */6 * * *",
            relevance_threshold=0.6,
            must_include=["local llm", "agent"],
        )
        topic = await svc.create_topic(data)
        await db_session.flush()

        assert topic.topic_id is not None
        assert topic.name == "로컬 LLM 에이전트"
        assert topic.priority == 8

    async def test_disable_topic(self, db_session, sample_topic):
        """TC-T02: 주제 비활성화 — enabled=False 설정."""
        db_session.add(sample_topic)
        await db_session.flush()

        svc = TopicService(db_session)
        updated = await svc.update_topic(sample_topic.topic_id, TopicUpdate(enabled=False))

        assert updated is not None
        assert updated.enabled is False

    async def test_list_topics_sorted_by_priority(self, db_session):
        """TC-T03: 우선순위 오름차순 정렬 조회."""
        svc = TopicService(db_session)
        for priority in [10, 1, 5]:
            await svc.create_topic(TopicCreate(
                name=f"주제-{priority}",
                description="테스트",
                priority=priority,
                schedule_cron="0 */6 * * *",
            ))
        await db_session.flush()

        topics = await svc.list_topics()
        priorities = [t.priority for t in topics]
        assert priorities == sorted(priorities)

    async def test_add_rule(self, db_session, sample_topic):
        """TC-T04: 도메인 룰 등록."""
        db_session.add(sample_topic)
        await db_session.flush()

        svc = TopicService(db_session)
        rule = await svc.add_rule(
            sample_topic.topic_id,
            TopicRuleCreate(
                rule_type="preferred_domain",
                pattern=r"github\.com",
                is_regex=True,
            ),
        )
        await db_session.flush()

        assert rule.rule_id is not None
        assert rule.topic_id == sample_topic.topic_id
        assert rule.rule_type == "preferred_domain"

    async def test_delete_topic(self, db_session, sample_topic):
        """주제 삭제."""
        db_session.add(sample_topic)
        await db_session.flush()

        svc = TopicService(db_session)
        result = await svc.delete_topic(sample_topic.topic_id)
        assert result is True

        # 재조회 시 None
        deleted = await svc.get_topic(sample_topic.topic_id)
        assert deleted is None

    async def test_get_nonexistent_topic_returns_none(self, db_session):
        """존재하지 않는 주제 조회 시 None."""
        svc = TopicService(db_session)
        result = await svc.get_topic("nonexistent-id")
        assert result is None
