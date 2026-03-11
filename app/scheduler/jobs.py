"""스케줄러 잡 정의 및 동적 등록 (FR-SC01~SC03)."""

import asyncio

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.scheduler.scheduler import scheduler

logger = get_logger(__name__)


async def _run_topic_pipeline(topic_id: str) -> None:
    """단일 주제에 대한 수집 파이프라인을 실행합니다 (TC-SC01)."""
    from app.core.pipeline import CollectionPipeline
    from app.models.topic import Topic

    logger.info("스케줄된 파이프라인 시작", topic_id=topic_id)

    async with AsyncSessionLocal() as db:
        topic = await db.get(Topic, topic_id)
        if topic is None or not topic.enabled:
            logger.warning("비활성 또는 미존재 주제, 스킵", topic_id=topic_id)
            return

        # providers는 앱 상태에서 가져와야 하므로 지연 임포트
        from app.core.app_state import get_providers, get_search_provider
        providers = get_providers()
        search_provider = get_search_provider()

        pipeline = CollectionPipeline(
            db=db,
            providers=providers,
            search_provider=search_provider,
        )
        await pipeline.run(topic)


def run_topic_pipeline_sync(topic_id: str) -> None:
    """APScheduler가 호출하는 동기 래퍼."""
    asyncio.run(_run_topic_pipeline(topic_id))


async def _reset_daily_token_usage() -> None:
    """일일 토큰 사용량 초기화 (FR-SC02, TC-M04)."""
    from app.services.usage_service import UsageService

    async with AsyncSessionLocal() as db:
        svc = UsageService(db)
        count = await svc.reset_daily_usage()
        await db.commit()
        logger.info("일일 토큰 리셋 완료", models_reset=count)


def reset_daily_token_usage_sync() -> None:
    asyncio.run(_reset_daily_token_usage())


async def _run_archive_rotation() -> None:
    """아카이브 tier 전환 (FR-SC03)."""
    from app.services.archive_service import ArchiveService

    async with AsyncSessionLocal() as db:
        svc = ArchiveService(db)
        result = await svc.run_archive_rotation()
        await db.commit()
        logger.info("아카이브 tier 전환 완료", **result)


def run_archive_rotation_sync() -> None:
    asyncio.run(_run_archive_rotation())


async def register_topic_jobs() -> None:
    """활성 주제의 cron 잡을 스케줄러에 등록합니다 (FR-SC01)."""
    from app.models.topic import Topic

    async with AsyncSessionLocal() as db:
        stmt = select(Topic).where(Topic.enabled == True)
        topics = list((await db.execute(stmt)).scalars())

    for topic in topics:
        job_id = f"topic_{topic.topic_id}"
        # 기존 잡 제거 후 재등록
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        parts = topic.schedule_cron.split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            scheduler.add_job(
                run_topic_pipeline_sync,
                trigger="cron",
                id=job_id,
                args=[topic.topic_id],
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                replace_existing=True,
            )
            logger.info("주제 잡 등록", topic=topic.name, cron=topic.schedule_cron)


def register_system_jobs() -> None:
    """시스템 고정 잡을 등록합니다."""
    # 일일 토큰 리셋 (자정 Asia/Seoul)
    scheduler.add_job(
        reset_daily_token_usage_sync,
        trigger="cron",
        id="reset_daily_tokens",
        hour=0,
        minute=0,
        replace_existing=True,
    )

    # 아카이브 tier 전환 (새벽 3시)
    scheduler.add_job(
        run_archive_rotation_sync,
        trigger="cron",
        id="archive_rotation",
        hour=3,
        minute=0,
        replace_existing=True,
    )

    logger.info("시스템 잡 등록 완료")
