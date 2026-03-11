"""APScheduler 기반 스케줄러 초기화."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# 전역 스케줄러 인스턴스
scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)


def get_scheduler() -> AsyncIOScheduler:
    return scheduler


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("스케줄러 시작", timezone=settings.scheduler_timezone)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("스케줄러 종료")
