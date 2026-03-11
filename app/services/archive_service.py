"""Archive Service — 파일시스템 원문 저장 및 문서 버전 관리."""

import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import Document, DocumentVersion, RawDocument

logger = get_logger(__name__)


def _url_to_filename(url: str) -> str:
    """URL을 안전한 파일명으로 변환합니다 (Windows 호환)."""
    return hashlib.md5(url.encode()).hexdigest()[:16]


class ArchiveService:
    """원문 파일 저장 및 문서 버전 관리 서비스 (FR-S01~S04)."""

    def __init__(self, db: AsyncSession):
        self._db = db

    def get_raw_path(self, url: str, fetch_date: Optional[date] = None) -> Path:
        """원문 HTML 저장 경로를 반환합니다."""
        d = fetch_date or date.today()
        filename = _url_to_filename(url)
        return settings.raw_base_path / d.strftime("%Y/%m/%d") / f"{filename}.html"

    async def save_raw_html(self, url: str, html_bytes: bytes) -> tuple[str, Path]:
        """원문 HTML을 파일시스템에 저장합니다 (FR-S01).

        Returns:
            (content_hash, 저장 경로)
        """
        content_hash = hashlib.sha256(html_bytes).hexdigest()
        path = self.get_raw_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(path, "wb") as f:
            await f.write(html_bytes)

        return content_hash, path

    async def get_or_create_raw_document(
        self, url: str, content_hash: str, html_path: Path, http_status: int
    ) -> tuple[RawDocument, bool]:
        """RawDocument를 생성하거나 기존 레코드를 반환합니다.

        Returns:
            (RawDocument, is_new)
        """
        stmt = select(RawDocument).where(
            RawDocument.url == url,
            RawDocument.content_hash == content_hash,
        )
        existing = (await self._db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing, False

        raw_doc = RawDocument(
            url=url,
            fetched_at=datetime.now(timezone.utc),
            http_status=http_status,
            content_hash=content_hash,
            raw_html_path=str(html_path),
        )
        self._db.add(raw_doc)
        return raw_doc, True

    async def upsert_document(
        self,
        topic_id: str,
        url: str,
        content_hash: str,
        normalized_text: str,
        title: Optional[str],
        author: Optional[str],
        published_at: Optional[datetime],
        language: Optional[str],
        summary: Optional[str],
        relevance_score: float,
        relevance_reason: str,
    ) -> tuple[Document, bool]:
        """문서를 저장하거나 내용 변경 시 버전을 증가시킵니다 (TC-S01~S03, FR-S02~S04).

        Returns:
            (Document, is_new_version)
        """
        # 기존 문서 조회
        stmt = select(Document).where(Document.url == url)
        existing = (await self._db.execute(stmt)).scalar_one_or_none()

        if existing:
            # content_hash가 동일하면 저장 스킵 (TC-S03, FR-S04)
            if existing.normalized_text and hashlib.sha256(
                existing.normalized_text.encode()
            ).hexdigest() == content_hash:
                return existing, False

            # 내용 변경: 버전 증가 (TC-S02, FR-S03)
            new_version = existing.current_version + 1
            version = DocumentVersion(
                doc_id=existing.doc_id,
                version_no=new_version,
                content_hash=content_hash,
                normalized_text=normalized_text,
                summary=summary,
                relevance_score=relevance_score,
                created_at=datetime.now(timezone.utc),
                change_type="update",
            )
            self._db.add(version)

            existing.current_version = new_version
            existing.normalized_text = normalized_text
            existing.summary = summary
            existing.relevance_score = relevance_score
            existing.relevance_reason = relevance_reason
            existing.collected_at = datetime.now(timezone.utc)
            existing.title = title or existing.title
            self._db.add(existing)

            logger.info("문서 버전 증가", url=url[:80], version=new_version)
            return existing, True

        # 신규 문서 저장 (TC-S01)
        doc = Document(
            topic_id=topic_id,
            url=url,
            title=title,
            author=author,
            published_at=published_at,
            collected_at=datetime.now(timezone.utc),
            language=language,
            normalized_text=normalized_text,
            summary=summary,
            relevance_score=relevance_score,
            relevance_reason=relevance_reason,
            current_version=1,
        )
        self._db.add(doc)
        await self._db.flush()  # doc_id 생성

        version = DocumentVersion(
            doc_id=doc.doc_id,
            version_no=1,
            content_hash=content_hash,
            normalized_text=normalized_text,
            summary=summary,
            relevance_score=relevance_score,
            created_at=datetime.now(timezone.utc),
            change_type="initial",
        )
        self._db.add(version)

        logger.info("신규 문서 저장", url=url[:80], doc_id=doc.doc_id)
        return doc, True

    async def run_archive_rotation(self) -> dict:
        """아카이브 tier 전환 (FR-SC03).

        - 90일 경과 + relevance < 0.5 → active → warm
        - 365일 경과 → warm → cold
        """
        from datetime import timedelta
        from sqlalchemy import update

        now = datetime.now(timezone.utc)
        warm_cutoff = now - timedelta(days=settings.archive_warm_after_days)
        cold_cutoff = now - timedelta(days=settings.archive_cold_after_days)

        # active → warm
        warm_stmt = (
            select(Document)
            .where(
                Document.archive_tier == "active",
                Document.collected_at <= warm_cutoff,
                Document.relevance_score < 0.5,
            )
        )
        warm_docs = list((await self._db.execute(warm_stmt)).scalars())
        for d in warm_docs:
            d.archive_tier = "warm"

        # warm → cold
        cold_stmt = (
            select(Document)
            .where(
                Document.archive_tier == "warm",
                Document.collected_at <= cold_cutoff,
            )
        )
        cold_docs = list((await self._db.execute(cold_stmt)).scalars())
        for d in cold_docs:
            d.archive_tier = "cold"

        logger.info(
            "아카이브 tier 전환",
            to_warm=len(warm_docs),
            to_cold=len(cold_docs),
        )
        return {"to_warm": len(warm_docs), "to_cold": len(cold_docs)}
