"""Topic Service — 주제 CRUD."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.topic import Topic, TopicRule
from app.api.schemas.topic import TopicCreate, TopicUpdate, TopicRuleCreate

logger = get_logger(__name__)


class TopicService:
    """주제 등록·수정·삭제·조회 서비스 (FR-T01~T04)."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_topic(self, data: TopicCreate) -> Topic:
        """주제를 생성하고 초기 규칙을 함께 등록합니다 (TC-T01)."""
        topic = Topic(
            name=data.name,
            description=data.description,
            language=data.language,
            priority=data.priority,
            enabled=data.enabled,
            schedule_cron=data.schedule_cron,
            relevance_threshold=data.relevance_threshold,
            must_include=data.must_include,
            must_exclude=data.must_exclude,
        )
        self._db.add(topic)
        await self._db.flush()  # topic_id 생성

        for rule_data in data.rules:
            rule = TopicRule(
                topic_id=topic.topic_id,
                rule_type=rule_data.rule_type,
                pattern=rule_data.pattern,
                is_regex=rule_data.is_regex,
                enabled=rule_data.enabled,
                priority=rule_data.priority,
            )
            self._db.add(rule)

        logger.info("주제 생성", topic_id=topic.topic_id, name=topic.name)
        return topic

    async def get_topic(self, topic_id: str) -> Topic | None:
        return await self._db.get(Topic, topic_id)

    async def list_topics(self, enabled_only: bool = False) -> list[Topic]:
        """주제 목록을 priority 오름차순으로 반환합니다 (TC-T03, FR-T04)."""
        stmt = select(Topic).order_by(Topic.priority, Topic.name)
        if enabled_only:
            stmt = stmt.where(Topic.enabled == True)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_topic(self, topic_id: str, data: TopicUpdate) -> Topic | None:
        """주제를 수정합니다 (TC-T02)."""
        topic = await self._db.get(Topic, topic_id)
        if topic is None:
            return None

        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(topic, field, value)

        self._db.add(topic)
        logger.info("주제 수정", topic_id=topic_id)
        return topic

    async def delete_topic(self, topic_id: str) -> bool:
        """주제를 삭제합니다 (cascade로 연관 데이터도 삭제)."""
        topic = await self._db.get(Topic, topic_id)
        if topic is None:
            return False
        await self._db.delete(topic)
        logger.info("주제 삭제", topic_id=topic_id)
        return True

    async def add_rule(self, topic_id: str, data: TopicRuleCreate) -> TopicRule:
        """주제에 룰을 추가합니다 (TC-T04, FR-T03)."""
        rule = TopicRule(
            topic_id=topic_id,
            rule_type=data.rule_type,
            pattern=data.pattern,
            is_regex=data.is_regex,
            enabled=data.enabled,
            priority=data.priority,
        )
        self._db.add(rule)
        return rule

    async def update_rule(self, rule_id: str, data: dict) -> TopicRule | None:
        rule = await self._db.get(TopicRule, rule_id)
        if rule is None:
            return None
        for field, value in data.items():
            if value is not None:
                setattr(rule, field, value)
        self._db.add(rule)
        return rule

    async def delete_rule(self, rule_id: str) -> bool:
        rule = await self._db.get(TopicRule, rule_id)
        if rule is None:
            return False
        await self._db.delete(rule)
        return True
