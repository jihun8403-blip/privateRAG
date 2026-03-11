"""15단계 수집 파이프라인 오케스트레이터."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.document import Document
from app.models.run_log import SearchRun
from app.models.topic import SearchQuery, Topic
from app.providers.extractor.chain import ExtractionPipeline
from app.providers.llm.base import BaseLLMProvider
from app.providers.search.base import BaseSearchProvider, SearchResult
from app.services.archive_service import ArchiveService
from app.services.fetch_service import FetchService
from app.services.model_router import ModelRouter
from app.services.query_planner import QueryPlanner
from app.services.rag_service import RagService
from app.services.relevance_service import RelevanceService
from app.services.rule_engine import RuleSet, classify_url
from app.services.search_service import SearchService
from app.services.usage_service import UsageService

logger = get_logger(__name__)


@dataclass
class PipelineContext:
    """파이프라인 단계 간 공유 상태."""
    topic: Topic
    run: SearchRun
    rule_set: Optional[RuleSet] = None
    queries: list[SearchQuery] = field(default_factory=list)
    search_results: list[SearchResult] = field(default_factory=list)
    filtered_urls: list[str] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


class CollectionPipeline:
    """15단계 자동 수집·검증·인덱싱 파이프라인 (SDS §4.5).

    단계:
    1.  topic load (규칙 포함)
    2.  query generate
    3.  search
    4.  url filter
    5.  dedup
    6.  fetch
    7.  extract
    8.  rule-based filter (1차)
    9.  llm relevance check (2차)
    10. normalize & summarize
    11. archive raw
    12. upsert document + versioning
    13. chunking
    14. embedding
    15. qdrant index + log
    """

    def __init__(
        self,
        db: AsyncSession,
        providers: dict[str, BaseLLMProvider],
        search_provider: BaseSearchProvider,
    ):
        self._db = db
        self._router = ModelRouter(db, providers)
        self._query_planner = QueryPlanner(db, self._router)
        self._search_service = SearchService(db, search_provider)
        self._fetch_service = FetchService()
        self._extraction_pipeline = ExtractionPipeline()
        self._relevance_service = RelevanceService(self._router)
        self._archive_service = ArchiveService(db)
        self._rag_service = RagService(db, self._router)
        self._usage_service = UsageService(db)

    async def run(self, topic: Topic) -> SearchRun:
        """파이프라인을 실행하고 SearchRun을 반환합니다."""
        run = SearchRun(
            topic_id=topic.topic_id,
            provider="pipeline",
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        self._db.add(run)
        await self._db.flush()

        ctx = PipelineContext(topic=topic, run=run)

        steps = [
            ("topic_load", self._step_topic_load),
            ("query_generate", self._step_query_generate),
            ("search", self._step_search),
            ("url_filter", self._step_url_filter),
            ("fetch_and_process", self._step_fetch_and_process),
            ("index", self._step_index),
        ]

        try:
            for step_name, step_fn in steps:
                logger.info("파이프라인 단계 시작", step=step_name, topic=topic.name)
                ctx = await step_fn(ctx)
                logger.info(
                    "파이프라인 단계 완료",
                    step=step_name,
                    docs=len(ctx.documents),
                )

            run.status = "success"
            run.result_count = len(ctx.documents)
        except Exception as e:
            logger.error("파이프라인 오류", step="unknown", error=str(e), topic=topic.name)
            run.status = "failed"
            run.error_message = str(e)

        run.finished_at = datetime.now(timezone.utc)
        self._db.add(run)
        await self._db.commit()

        return run

    async def _step_topic_load(self, ctx: PipelineContext) -> PipelineContext:
        """[1] 주제 및 규칙 로드."""
        ctx.rule_set = RuleSet(ctx.topic.rules)
        return ctx

    async def _step_query_generate(self, ctx: PipelineContext) -> PipelineContext:
        """[2] LLM 검색 쿼리 생성."""
        ctx.queries = await self._query_planner.generate_queries(ctx.topic)
        await self._db.flush()
        return ctx

    async def _step_search(self, ctx: PipelineContext) -> PipelineContext:
        """[3] 검색 API 실행."""
        if not ctx.queries:
            logger.warning("쿼리 없음, 검색 스킵")
            return ctx

        _, filtered_urls = await self._search_service.run_search(
            topic=ctx.topic,
            queries=ctx.queries,
            rule_set=ctx.rule_set,
        )
        ctx.filtered_urls = filtered_urls
        await self._db.flush()
        return ctx

    async def _step_url_filter(self, ctx: PipelineContext) -> PipelineContext:
        """[4-5] URL 필터링 및 중복 제거 (이미 SearchService에서 처리됨)."""
        ctx.stats["url_count"] = len(ctx.filtered_urls)
        return ctx

    async def _step_fetch_and_process(self, ctx: PipelineContext) -> PipelineContext:
        """[6-12] URL별 수집·추출·검증·저장."""
        for url in ctx.filtered_urls:
            try:
                await self._process_single_url(ctx, url)
            except Exception as e:
                logger.warning("URL 처리 실패 (건너뜀)", url=url[:80], error=str(e))

        await self._db.flush()
        return ctx

    async def _process_single_url(self, ctx: PipelineContext, url: str) -> None:
        """단일 URL을 6~12단계로 처리합니다."""
        # [6] HTTP 수집
        try:
            html_bytes, http_status, final_url = await self._fetch_service.fetch_url(url)
        except Exception as e:
            logger.warning("수집 실패", url=url[:80], error=str(e))
            return

        # [7] 본문 추출
        try:
            html_str = html_bytes.decode("utf-8", errors="replace")
            extract_result = await self._extraction_pipeline.extract(html_str, final_url)
        except Exception as e:
            logger.warning("추출 실패", url=url[:80], error=str(e))
            return

        text = extract_result.text

        # [8] 1차 규칙 기반 필터
        passed, reason = self._relevance_service.rule_filter(text, ctx.topic)
        if not passed:
            logger.debug("1차 필터 탈락", url=url[:80], reason=reason)
            return

        # [9] 2차 LLM 관련성 검증
        relevance_result = await self._relevance_service.llm_check(
            text, ctx.topic, title=extract_result.title or ""
        )
        if not relevance_result.is_relevant:
            logger.debug("LLM 검증 탈락", url=url[:80], score=relevance_result.score)
            return

        # [10] 원문 저장
        content_hash, raw_path = await self._archive_service.save_raw_html(url, html_bytes)

        # [11-12] 문서 upsert + 버전 관리
        doc, is_new = await self._archive_service.upsert_document(
            topic_id=ctx.topic.topic_id,
            url=final_url,
            content_hash=content_hash,
            normalized_text=text,
            title=extract_result.title,
            author=extract_result.author,
            published_at=extract_result.published_at,
            language=extract_result.language,
            summary=None,  # 요약은 별도 배치 처리
            relevance_score=relevance_result.score,
            relevance_reason=relevance_result.reason,
        )

        if is_new:
            ctx.documents.append(doc)

    async def _step_index(self, ctx: PipelineContext) -> PipelineContext:
        """[13-15] 청킹·임베딩·Qdrant 인덱스."""
        for doc in ctx.documents:
            try:
                chunks = await self._rag_service.chunk_document(doc)
                await self._db.flush()
                if chunks:
                    await self._rag_service.embed_chunks(chunks)
            except Exception as e:
                logger.warning("인덱싱 실패", doc_id=doc.doc_id, error=str(e))

        return ctx
