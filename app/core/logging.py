"""structlog 기반 구조화 로깅 설정."""

import logging
import sys

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """애플리케이션 로깅을 초기화합니다. main.py lifespan에서 호출."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.debug:
        # 개발 환경: 컬러 콘솔 출력
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # 프로덕션: JSON 출력
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # stdlib 로깅도 structlog으로 라우팅 (APScheduler, SQLAlchemy 로그 포함)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    # SQLAlchemy echo 억제 (debug=True일 때만 활성화)
    if not settings.debug:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("apscheduler").setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """모듈별 로거를 반환합니다."""
    return structlog.get_logger(name)
