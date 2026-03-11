"""Archive Service 통합 테스트 (TC-S01~S04)."""

import hashlib
from datetime import datetime, timezone

import pytest

from app.services.archive_service import ArchiveService


class TestArchiveService:
    async def test_save_new_document(self, db_session, sample_topic):
        """TC-S01: 신규 문서 저장 — documents + document_versions version_no=1."""
        db_session.add(sample_topic)
        await db_session.flush()

        svc = ArchiveService(db_session)
        text = "local llm agent framework test " * 20
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        doc, is_new = await svc.upsert_document(
            topic_id=sample_topic.topic_id,
            url="https://github.com/x/y",
            content_hash=content_hash,
            normalized_text=text,
            title="Test Doc",
            author=None,
            published_at=None,
            language="en",
            summary=None,
            relevance_score=0.85,
            relevance_reason="관련 있음",
        )
        await db_session.flush()

        assert is_new is True
        assert doc.doc_id is not None
        assert doc.current_version == 1
        assert doc.relevance_score == pytest.approx(0.85)

    async def test_same_url_changed_content_increments_version(
        self, db_session, sample_topic
    ):
        """TC-S02: 동일 URL 내용 변경 시 버전 증가."""
        db_session.add(sample_topic)
        await db_session.flush()

        svc = ArchiveService(db_session)
        url = "https://github.com/x/y"
        text_v1 = "local llm agent " * 20
        hash_v1 = hashlib.sha256(text_v1.encode()).hexdigest()

        # 1차 저장
        doc, _ = await svc.upsert_document(
            topic_id=sample_topic.topic_id,
            url=url,
            content_hash=hash_v1,
            normalized_text=text_v1,
            title="V1",
            author=None,
            published_at=None,
            language="en",
            summary=None,
            relevance_score=0.8,
            relevance_reason="",
        )
        await db_session.flush()
        assert doc.current_version == 1

        # 내용 변경 후 재저장
        text_v2 = "local llm agent updated version 2 " * 20
        hash_v2 = hashlib.sha256(text_v2.encode()).hexdigest()

        doc2, is_new = await svc.upsert_document(
            topic_id=sample_topic.topic_id,
            url=url,
            content_hash=hash_v2,
            normalized_text=text_v2,
            title="V2",
            author=None,
            published_at=None,
            language="en",
            summary=None,
            relevance_score=0.85,
            relevance_reason="",
        )
        await db_session.flush()

        assert is_new is True
        assert doc2.current_version == 2
        assert doc2.doc_id == doc.doc_id  # 같은 레코드

    async def test_same_content_no_new_version(self, db_session, sample_topic):
        """TC-S03: 동일 URL + 동일 content → 새 버전 미생성 (FR-S04)."""
        db_session.add(sample_topic)
        await db_session.flush()

        svc = ArchiveService(db_session)
        url = "https://github.com/x/z"
        text = "local llm agent " * 20
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        # 1차
        doc, is_new1 = await svc.upsert_document(
            topic_id=sample_topic.topic_id,
            url=url,
            content_hash=content_hash,
            normalized_text=text,
            title="Test",
            author=None,
            published_at=None,
            language="en",
            summary=None,
            relevance_score=0.8,
            relevance_reason="",
        )
        await db_session.flush()

        # 2차 (동일 내용)
        doc2, is_new2 = await svc.upsert_document(
            topic_id=sample_topic.topic_id,
            url=url,
            content_hash=content_hash,  # 동일 hash
            normalized_text=text,
            title="Test",
            author=None,
            published_at=None,
            language="en",
            summary=None,
            relevance_score=0.8,
            relevance_reason="",
        )

        assert is_new1 is True
        assert is_new2 is False
        assert doc.current_version == 1
