"""Rules API 라우터 (SDS §6.2)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import DbDep
from app.api.schemas.topic import TopicRuleCreate, TopicRuleRead, TopicRuleUpdate
from app.services.rule_engine import RuleSet, classify_url
from app.services.topic_service import TopicService

router = APIRouter()


@router.get("/topics/{topic_id}/rules", response_model=list[TopicRuleRead])
async def list_rules(topic_id: str, db: DbDep):
    """주제별 룰 목록 조회."""
    svc = TopicService(db)
    topic = await svc.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다.")
    return topic.rules


@router.post("/topics/{topic_id}/rules", response_model=TopicRuleRead, status_code=201)
async def create_rule(topic_id: str, data: TopicRuleCreate, db: DbDep):
    """주제에 룰 추가 (TC-T04)."""
    svc = TopicService(db)
    topic = await svc.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다.")
    return await svc.add_rule(topic_id, data)


@router.put("/rules/{rule_id}", response_model=TopicRuleRead)
async def update_rule(rule_id: str, data: TopicRuleUpdate, db: DbDep):
    """룰 수정."""
    svc = TopicService(db)
    rule = await svc.update_rule(rule_id, data.model_dump(exclude_none=True))
    if rule is None:
        raise HTTPException(status_code=404, detail="룰을 찾을 수 없습니다.")
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, db: DbDep):
    """룰 삭제."""
    svc = TopicService(db)
    deleted = await svc.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="룰을 찾을 수 없습니다.")


class RuleTestRequest(BaseModel):
    url: str
    topic_id: str


class RuleTestResponse(BaseModel):
    result: str
    matched_rule: str | None


@router.post("/rules/test", response_model=RuleTestResponse)
async def test_rule(data: RuleTestRequest, db: DbDep):
    """임의 URL에 대한 룰 매칭 테스트 (TC-R05, FR-D03)."""
    svc = TopicService(db)
    topic = await svc.get_topic(data.topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다.")

    rule_set = RuleSet(topic.rules)
    classification, matched = classify_url(data.url, rule_set)

    return RuleTestResponse(result=classification, matched_rule=matched)
