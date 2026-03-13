# SDS — Software Design Specification

**버전**: 1.0
**작성일**: 2026-03-11
**상태**: Draft

---

## 1. 시스템 아키텍처 개요

### 1.1 레이어 구조

```
┌─────────────────────────────────────┐
│          API Layer (FastAPI)        │
├─────────────────────────────────────┤
│         Service Layer               │
│  topic / query / search / fetch     │
│  relevance / rag / model / usage    │
├─────────────────────────────────────┤
│         Provider Layer              │
│   llm / search / extractor          │
├─────────────────────────────────────┤
│      Scheduler (APScheduler)        │
├─────────────────────────────────────┤
│         Data Layer                  │
│  SQLite(ORM) │ FileSystem │ Qdrant  │
└─────────────────────────────────────┘
```

### 1.2 핵심 설계 원칙

1. **주제와 질의 분리** — 주제는 사람이 정의, 질의는 시스템이 생성
2. **원문과 RAG 가공본 분리** — 증거 보관과 검색 최적화의 목적 구분
3. **모델과 작업 분리** — 파이프라인은 모델 이름을 몰라야 한다
4. **현재 상태와 이력 분리** — active view + immutable log 이중 구조
5. **규칙 기반 + LLM 판단 혼합** — 비용·속도·품질의 계단형 조합

---

## 2. 디렉터리 구조

```
project/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── topics.py
│   │   │   ├── rules.py
│   │   │   ├── documents.py
│   │   │   ├── search.py
│   │   │   ├── rag.py
│   │   │   └── models.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── pipeline.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── migrations/
│   ├── models/
│   │   ├── topic.py
│   │   ├── document.py
│   │   ├── chunk.py
│   │   ├── model_registry.py
│   │   └── run_log.py
│   ├── services/
│   │   ├── topic_service.py
│   │   ├── query_planner.py
│   │   ├── search_service.py
│   │   ├── fetch_service.py
│   │   ├── relevance_service.py
│   │   ├── summary_service.py   ← 문서 AI 요약 (2026-03-13 추가)
│   │   ├── archive_service.py
│   │   ├── rag_service.py
│   │   ├── model_router.py
│   │   └── usage_service.py
│   ├── providers/
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── ollama_adapter.py
│   │   │   ├── openai_adapter.py
│   │   │   ├── anthropic_adapter.py
│   │   │   ├── gemini_adapter.py
│   │   │   └── google_adapter.py   ← Gemini (OpenAI 호환, 2026-03-11 추가)
│   │   ├── search/
│   │   │   ├── base.py
│   │   │   └── brave_adapter.py
│   │   └── extractor/
│   │       ├── base.py
│   │       ├── trafilatura_extractor.py
│   │       ├── readability_extractor.py
│   │       └── playwright_extractor.py
│   └── scheduler/
│       ├── scheduler.py
│       └── jobs.py
├── data/
│   ├── raw/YYYY/MM/DD/
│   ├── normalized/
│   ├── archive/
│   └── index/
├── tests/
├── scripts/
├── config/
│   └── settings.yaml
└── main.py
```

---

## 3. 데이터베이스 스키마

### 3.1 topics

```sql
CREATE TABLE topics (
    topic_id    TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    language    TEXT NOT NULL DEFAULT 'ko,en',
    priority    INTEGER NOT NULL DEFAULT 5,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    schedule_cron TEXT NOT NULL DEFAULT '0 */6 * * *',
    relevance_threshold REAL NOT NULL DEFAULT 0.6,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 topic_rules

```sql
CREATE TABLE topic_rules (
    rule_id     TEXT PRIMARY KEY,
    topic_id    TEXT NOT NULL REFERENCES topics(topic_id),
    rule_type   TEXT NOT NULL,  -- preferred_domain | blocked_domain | include | exclude
    pattern     TEXT NOT NULL,
    is_regex    BOOLEAN NOT NULL DEFAULT TRUE,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    priority    INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 search_queries

```sql
CREATE TABLE search_queries (
    query_id          TEXT PRIMARY KEY,
    topic_id          TEXT NOT NULL REFERENCES topics(topic_id),
    query_text        TEXT NOT NULL,
    query_language    TEXT NOT NULL,
    intent            TEXT NOT NULL,  -- broad | narrow | preferred_domain
    generated_by_model TEXT,
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at        DATETIME
);
```

### 3.4 search_runs

```sql
CREATE TABLE search_runs (
    run_id        TEXT PRIMARY KEY,
    topic_id      TEXT NOT NULL REFERENCES topics(topic_id),
    query_id      TEXT REFERENCES search_queries(query_id),
    provider      TEXT NOT NULL,
    started_at    DATETIME NOT NULL,
    finished_at   DATETIME,
    status        TEXT NOT NULL,  -- running | success | failed
    result_count  INTEGER DEFAULT 0,
    error_message TEXT
);
```

### 3.5 raw_documents

```sql
CREATE TABLE raw_documents (
    raw_doc_id    TEXT PRIMARY KEY,
    url           TEXT NOT NULL,
    fetched_at    DATETIME NOT NULL,
    http_status   INTEGER,
    content_hash  TEXT NOT NULL,
    raw_html_path TEXT,
    raw_json_path TEXT
);
CREATE UNIQUE INDEX idx_raw_documents_hash ON raw_documents(url, content_hash);
```

### 3.6 documents

```sql
CREATE TABLE documents (
    doc_id            TEXT PRIMARY KEY,
    topic_id          TEXT NOT NULL REFERENCES topics(topic_id),
    url               TEXT NOT NULL UNIQUE,
    title             TEXT,
    author            TEXT,
    published_at      DATETIME,
    collected_at      DATETIME NOT NULL,
    language          TEXT,
    normalized_text   TEXT,
    summary           TEXT,
    relevance_score   REAL,
    relevance_reason  TEXT,
    current_version   INTEGER NOT NULL DEFAULT 1,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    archive_tier      TEXT NOT NULL DEFAULT 'active',  -- active | warm | cold
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 3.7 document_versions

```sql
CREATE TABLE document_versions (
    version_id      TEXT PRIMARY KEY,
    doc_id          TEXT NOT NULL REFERENCES documents(doc_id),
    version_no      INTEGER NOT NULL,
    content_hash    TEXT NOT NULL,
    normalized_text TEXT,
    summary         TEXT,
    relevance_score REAL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    change_type     TEXT NOT NULL  -- initial | update | revalidated
);
```

### 3.8 chunks

```sql
CREATE TABLE chunks (
    chunk_id         TEXT PRIMARY KEY,
    doc_id           TEXT NOT NULL REFERENCES documents(doc_id),
    version_no       INTEGER NOT NULL,
    chunk_index      INTEGER NOT NULL,
    chunk_text       TEXT NOT NULL,
    token_count      INTEGER,
    embedding_model  TEXT,
    embedding_status TEXT NOT NULL DEFAULT 'pending'  -- pending | done | failed
);
```

### 3.9 model_registry

```sql
CREATE TABLE model_registry (
    model_id             TEXT PRIMARY KEY,
    provider             TEXT NOT NULL,   -- openai | ollama | anthropic | gemini
    model_name           TEXT NOT NULL,
    capability_tags      TEXT NOT NULL,   -- JSON array: ["query_gen","relevance_check",...]
    max_context          INTEGER,
    cost_input_per_1k    REAL DEFAULT 0,
    cost_output_per_1k   REAL DEFAULT 0,
    daily_budget_tokens  INTEGER NOT NULL DEFAULT 999999999,
    used_tokens_today    INTEGER NOT NULL DEFAULT 0,
    priority             INTEGER NOT NULL DEFAULT 10,
    fallback_order       INTEGER NOT NULL DEFAULT 99,
    enabled              BOOLEAN NOT NULL DEFAULT TRUE,
    last_reset_date      DATE
);
```

### 3.10 model_usage_logs

```sql
CREATE TABLE model_usage_logs (
    usage_id      TEXT PRIMARY KEY,
    model_id      TEXT NOT NULL REFERENCES model_registry(model_id),
    task_type     TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_estimate REAL DEFAULT 0,
    executed_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status        TEXT NOT NULL  -- success | failed | skipped
);
```

---

## 4. 주요 서비스 설계

### 4.1 Query Planner

```python
class QueryPlanner:
    async def generate_queries(self, topic: Topic) -> list[SearchQuery]:
        """
        topic 프로필을 기반으로 LLM에 구조화된 쿼리 생성 요청
        반환: [{ query, intent, language }, ...]
        """
```

**출력 스키마**

```json
{
  "queries": [
    { "query": "...", "intent": "broad", "language": "en" },
    { "query": "...", "intent": "preferred_domain", "language": "en" },
    { "query": "...", "intent": "broad", "language": "ko" }
  ]
}
```

### 4.2 Model Router

```python
class ModelRouter:
    def select_model(
        self,
        task_type: str,
        required_capabilities: list[str],
        estimated_tokens: int,
        quality_preference: str = "medium"
    ) -> ModelCandidate:
        """
        capability 충족 + 예산 여유 + 우선순위 기준으로 모델 선택
        없으면 fallback chain 순서대로 시도
        """

    def can_run(self, model: ModelRegistry, estimated_tokens: int) -> bool:
        return (model.used_tokens_today + estimated_tokens) <= model.daily_budget_tokens
```

**Task 유형별 기본 모델 우선순위**

| task_type | primary | fallback |
|-----------|---------|----------|
| query_gen | API 소형 | 로컬 소형 |
| relevance_check | 로컬 소형 | API 소형 |
| summarize | 로컬 중형 | API 소형 |
| summary_gen | capability=answer 모델 | — |
| answer | 사용자 선택 | 로컬 중형 |
| rerank | 로컬 소형 | — |

### 4.3 URL Rule Engine

```python
def classify_url(url: str, rules: RuleSet) -> Literal["blocked", "preferred", "neutral"]:
    domain = get_domain(url)
    for rule in rules.blocked_url:
        if re.search(rule.pattern, url): return "blocked"
    for rule in rules.blocked_domain:
        if re.search(rule.pattern, domain): return "blocked"
    for rule in rules.preferred_url:
        if re.search(rule.pattern, url): return "preferred"
    for rule in rules.preferred_domain:
        if re.search(rule.pattern, domain): return "preferred"
    return "neutral"
```

### 4.4 Summary Service (2026-03-13 추가)

```python
class SummaryService:
    async def generate(self, doc: Document) -> dict:
        """
        1. FetchService로 URL 재수집
        2. ExtractionPipeline으로 본문 추출 (최대 8000자)
        3. ModelRouter.select_model(task_type="summary_gen", capability=["answer"])
        4. LLM으로 7개 섹션 Markdown 생성:
           핵심 요약 / 배경 / 대상 독자 / 의미·영향 / 섹션별 요약 / 실무 적용 방안 / 키워드
        5. Qdrant 벡터 검색으로 관련 문서 TOP5 (현재 문서 제외, doc_id별 dedupe)
        6. 관련 문서 Markdown 테이블을 요약에 append
        7. doc.summary 갱신 후 DB commit
        반환: {"summary": str, "related_docs": list[RelatedDocItem]}
        """
```

**응답 스키마**

```json
{
  "summary": "## 핵심 요약\n...",
  "related_docs": [
    { "doc_id": "...", "url": "...", "title": "...", "relevance_score": 0.87 }
  ]
}
```

### 4.5 Relevance Validator

```
1차 규칙 검사
├── must_include 키워드 중 1개 이상 존재?
├── must_exclude 키워드 없음?
├── 문서 길이 > 최소 기준(기본 200자)?
└── 언어 감지 일치?

통과 시 → 2차 LLM 검사
└── score, reason 반환
    → score >= topic.relevance_threshold → 저장
    → 미달 → 폐기 기록 후 skip
```

### 4.6 수집 파이프라인

```
[1]  topic load
[2]  query generate        ← query_planner
[3]  search retrieve       ← search provider
[4]  url/domain rule filter ← rule engine
[5]  url dedup
[6]  raw fetch             ← fetch_service
[7]  content extract       ← extractor (trafilatura → readability → playwright)
[8]  rule-based filter     ← relevance_service (1차)
[9]  llm relevance check   ← relevance_service (2차)
[10] normalize & summarize
[11] archive raw/original  ← archive_service
[12] upsert document + versioning
[13] chunking
[14] embedding             ← embedding provider
[15] rag index update      ← qdrant
[16] run log / usage log update
```

---

## 5. Provider 인터페이스

### 5.1 LLM Provider

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        response_format: dict | None = None,
        max_tokens: int = 1024
    ) -> LLMResponse:
        ...

class LLMResponse(BaseModel):
    content: str
    input_tokens: int
    output_tokens: int
    model_name: str
```

### 5.2 Search Provider

```python
class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        count: int = 10,
        language: str = "en"
    ) -> list[SearchResult]:
        ...

class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    published_at: datetime | None
```

### 5.3 Extractor Provider

```python
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, html: str, url: str) -> ExtractResult:
        ...

class ExtractResult(BaseModel):
    title: str | None
    text: str
    author: str | None
    published_at: datetime | None
    language: str | None
```

---

## 6. API 엔드포인트

### 6.1 Topics

| Method | Path | 설명 |
|--------|------|------|
| GET | /topics | 주제 목록 조회 |
| POST | /topics | 주제 생성 |
| GET | /topics/{id} | 주제 상세 |
| PUT | /topics/{id} | 주제 수정 |
| DELETE | /topics/{id} | 주제 삭제 |
| POST | /topics/{id}/run | 즉시 수집 실행 |

### 6.2 Rules

| Method | Path | 설명 |
|--------|------|------|
| GET | /topics/{id}/rules | 룰 목록 |
| POST | /topics/{id}/rules | 룰 생성 |
| PUT | /rules/{rule_id} | 룰 수정 |
| DELETE | /rules/{rule_id} | 룰 삭제 |
| POST | /rules/test | URL 룰 테스트 |

### 6.3 Documents

| Method | Path | 설명 |
|--------|------|------|
| GET | /documents | 문서 목록 (주제별 필터) |
| GET | /documents/{id} | 문서 상세 |
| GET | /documents/{id}/versions | 버전 이력 |
| GET | /documents/{id}/versions/{no} | 특정 버전 |
| POST | /documents/{id}/summary | AI 요약 생성 (2026-03-13 추가) |

### 6.4 RAG

| Method | Path | 설명 |
|--------|------|------|
| POST | /rag/query | 자연어 질의응답 |
| GET | /rag/chunks | 청크 검색 |

### 6.5 Models

| Method | Path | 설명 |
|--------|------|------|
| GET | /models | 모델 목록 |
| POST | /models | 모델 등록 |
| PUT | /models/{id} | 모델 수정 |
| GET | /models/{id}/usage | 사용량 조회 |
| POST | /models/reset-usage | 수동 토큰 리셋 |

---

## 7. 스케줄러 설계

```python
# jobs.py
scheduler.add_job(run_topic_pipeline, 'cron', args=[topic_id], ...)
scheduler.add_job(reset_daily_token_usage, 'cron', hour=0, minute=0, timezone='Asia/Seoul')
scheduler.add_job(run_archive_rotation, 'cron', hour=3, minute=0)
scheduler.add_job(refresh_expired_queries, 'cron', hour=4, minute=0)
```

**아카이브 티어 전환 기준**

| 조건 | 전환 |
|------|------|
| 수집 후 90일 경과 AND relevance_score < 0.5 | Active → Warm |
| 수집 후 365일 경과 | Warm → Cold |

---

## 8. 설정 파일

```yaml
# config/settings.yaml
database:
  url: "sqlite:///./data/privaterag.db"

storage:
  raw_base: "data/raw"
  normalized_base: "data/normalized"
  archive_base: "data/archive"

qdrant:
  url: "http://localhost:6333"
  collection: "privaterag"

embedding:
  model: "paraphrase-multilingual-mpnet-base-v2"
  dimension: 768

relevance:
  default_threshold: 0.6
  min_text_length: 200

archive:
  warm_after_days: 90
  cold_after_days: 365

search:
  brave_api_key: "${BRAVE_API_KEY}"
  default_count: 10
```

---

## 9. 기술 스택 확정

| 구분 | 선택 |
|------|------|
| 백엔드 프레임워크 | FastAPI |
| ORM | SQLAlchemy 2.x |
| 데이터 검증 | Pydantic v2 |
| DB (초기) | SQLite with FTS5 |
| DB (확장) | PostgreSQL |
| 벡터 저장소 | Qdrant |
| 임베딩 | sentence-transformers (multilingual) |
| 스케줄러 | APScheduler 3.x |
| 본문 추출 | trafilatura → readability-lxml → playwright |
| 로컬 LLM | Ollama (OpenAI 호환 API) |
| 언어 감지 | langdetect |
| 설정 관리 | pydantic-settings |
