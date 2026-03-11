"""Topics API 라우터 (SDS §6.1)."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.deps import DbDep
from app.api.schemas.topic import TopicCreate, TopicRead, TopicSummary, TopicUpdate
from app.services.topic_service import TopicService

router = APIRouter()


@router.get("", response_model=list[TopicSummary])
async def list_topics(db: DbDep):
    """주제 목록 조회 (우선순위 오름차순)."""
    svc = TopicService(db)
    return await svc.list_topics()


@router.post("", response_model=TopicRead, status_code=201)
async def create_topic(data: TopicCreate, db: DbDep):
    """주제 생성 (TC-T01)."""
    svc = TopicService(db)
    topic = await svc.create_topic(data)
    await db.flush()

    # 스케줄러에 동적 등록
    from app.scheduler.jobs import register_topic_jobs
    await register_topic_jobs()

    return topic


@router.get("/{topic_id}", response_model=TopicRead)
async def get_topic(topic_id: str, db: DbDep):
    """주제 상세 조회 (TC-API03)."""
    svc = TopicService(db)
    topic = await svc.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다.")
    return topic


@router.put("/{topic_id}", response_model=TopicRead)
async def update_topic(topic_id: str, data: TopicUpdate, db: DbDep):
    """주제 수정 (TC-T02)."""
    svc = TopicService(db)
    topic = await svc.update_topic(topic_id, data)
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다.")
    return topic


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(topic_id: str, db: DbDep):
    """주제 삭제."""
    svc = TopicService(db)
    deleted = await svc.delete_topic(topic_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다.")


@router.post("/{topic_id}/run", status_code=202)
async def run_topic_pipeline(
    topic_id: str,
    background_tasks: BackgroundTasks,
    db: DbDep,
):
    """즉시 수집 파이프라인 실행 (SDS §6.1 POST /topics/{id}/run)."""
    svc = TopicService(db)
    topic = await svc.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="주제를 찾을 수 없습니다.")

    from app.scheduler.jobs import _run_topic_pipeline
    background_tasks.add_task(_run_topic_pipeline, topic_id)

    return {"message": "수집 파이프라인이 시작되었습니다.", "topic_id": topic_id}
