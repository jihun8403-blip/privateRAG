# WBS — Work Breakdown Structure

**버전**: 1.0
**작성일**: 2026-03-11
**상태**: Draft

---

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 프로젝트명 | PrivateRAG |
| 목표 | 주제 중심 자동 수집·검증·검색 RAG 시스템 MVP 구축 |
| 범위 | 1차 MVP 전체 (백엔드 + CLI/API) |

---

## WBS 계층 구조

```
0. PrivateRAG 프로젝트
├── 1. 프로젝트 기반 구축
│   ├── 1.1 개발 환경 설정
│   ├── 1.2 프로젝트 구조 생성
│   └── 1.3 DB 초기화
├── 2. 데이터 모델 / ORM
│   ├── 2.1 DB 스키마 정의
│   └── 2.2 SQLAlchemy 모델 구현
├── 3. Provider 레이어
│   ├── 3.1 LLM Provider
│   ├── 3.2 Search Provider
│   └── 3.3 Extractor Provider
├── 4. 핵심 서비스 레이어
│   ├── 4.1 Topic Service
│   ├── 4.2 Rule Engine
│   ├── 4.3 Query Planner
│   ├── 4.4 Search Service
│   ├── 4.5 Fetch Service
│   ├── 4.6 Relevance Service
│   ├── 4.7 Archive Service
│   ├── 4.8 RAG Service
│   ├── 4.9 Model Router
│   └── 4.10 Usage Service
├── 5. 수집 파이프라인 통합
│   ├── 5.1 파이프라인 오케스트레이터
│   └── 5.2 스케줄러
├── 6. API 레이어 (FastAPI)
│   ├── 6.1 Topics API
│   ├── 6.2 Rules API
│   ├── 6.3 Documents API
│   ├── 6.4 RAG API
│   └── 6.5 Models API
├── 7. 테스트
│   ├── 7.1 단위 테스트
│   ├── 7.2 통합 테스트
│   └── 7.3 API 테스트
└── 8. 배포 및 운영 준비
    ├── 8.1 설정 파일 정비
    └── 8.2 수동 E2E 검증
```

---

## 상세 작업 목록

### 1. 프로젝트 기반 구축

#### 1.1 개발 환경 설정

| 작업 ID | 작업명 | 산출물 | 선행 작업 | 우선순위 |
|---------|--------|--------|-----------|----------|
| 1.1.1 | Python 가상환경 생성 (venv/conda) | 가상환경 | — | 필수 |
| 1.1.2 | 의존성 패키지 정의 (requirements.txt) | requirements.txt | 1.1.1 | 필수 |
| 1.1.3 | 패키지 설치 (FastAPI, SQLAlchemy, Pydantic, APScheduler, trafilatura, langdetect, sentence-transformers, qdrant-client) | 설치 완료 | 1.1.2 | 필수 |
| 1.1.4 | 환경변수 파일 구조 정의 (.env.example) | .env.example | — | 필수 |
| 1.1.5 | 코드 품질 도구 설정 (ruff, pytest, pytest-asyncio, pytest-cov, pytest-mock, freezegun) | pyproject.toml / pytest.ini | 1.1.1 | 권장 |

#### 1.2 프로젝트 구조 생성

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 1.2.1 | SDS 기반 디렉터리 구조 생성 | app/, data/, tests/, config/ 폴더 | 1.1.3 |
| 1.2.2 | config/settings.yaml 초안 작성 | settings.yaml | 1.2.1 |
| 1.2.3 | pydantic-settings 기반 Config 클래스 구현 | app/core/config.py | 1.2.2 |
| 1.2.4 | 로깅 설정 구현 | app/core/logging.py | 1.2.1 |

#### 1.3 DB 초기화

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 1.3.1 | SQLAlchemy Base + Session 설정 | app/db/base.py, session.py | 1.1.3 |
| 1.3.2 | Alembic 또는 create_all 초기화 스크립트 | scripts/init_db.py | 1.3.1 |

---

### 2. 데이터 모델 / ORM

#### 2.1 DB 스키마 정의

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 2.1.1 | topics, topic_rules 테이블 SQL | SDS §3.1, 3.2 | 1.3.1 |
| 2.1.2 | search_queries, search_runs 테이블 SQL | SDS §3.3, 3.4 | 1.3.1 |
| 2.1.3 | raw_documents, documents, document_versions 테이블 SQL | SDS §3.5~3.7 | 1.3.1 |
| 2.1.4 | chunks 테이블 SQL | SDS §3.8 | 2.1.3 |
| 2.1.5 | model_registry, model_usage_logs 테이블 SQL | SDS §3.9, 3.10 | 1.3.1 |

#### 2.2 SQLAlchemy ORM 모델 구현

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 2.2.1 | Topic, TopicRule ORM 클래스 | app/models/topic.py | 2.1.1 |
| 2.2.2 | SearchQuery, SearchRun ORM 클래스 | app/models/run_log.py | 2.1.2 |
| 2.2.3 | RawDocument, Document, DocumentVersion ORM 클래스 | app/models/document.py | 2.1.3 |
| 2.2.4 | Chunk ORM 클래스 | app/models/chunk.py | 2.1.4 |
| 2.2.5 | ModelRegistry, ModelUsageLog ORM 클래스 | app/models/model_registry.py | 2.1.5 |
| 2.2.6 | Pydantic 스키마 (Request/Response DTO) | app/api/schemas/ | 2.2.1~2.2.5 |

---

### 3. Provider 레이어

#### 3.1 LLM Provider

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 3.1.1 | BaseLLMProvider 추상 인터페이스 | app/providers/llm/base.py | 1.2.3 |
| 3.1.2 | OllamaAdapter 구현 (OpenAI 호환) | app/providers/llm/ollama_adapter.py | 3.1.1 |
| 3.1.3 | OpenAICompatibleAdapter 구현 | app/providers/llm/openai_adapter.py | 3.1.1 |
| 3.1.4 | AnthropicAdapter 구현 (선택) | app/providers/llm/anthropic_adapter.py | 3.1.1 |
| 3.1.5 | LLM Provider 단위 테스트 | tests/unit/providers/test_llm.py | 3.1.2, 3.1.3 |

#### 3.2 Search Provider

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 3.2.1 | BaseSearchProvider 추상 인터페이스 | app/providers/search/base.py | 1.2.3 |
| 3.2.2 | BraveSearchAdapter 구현 | app/providers/search/brave_adapter.py | 3.2.1 |
| 3.2.3 | Search Provider 단위 테스트 (Mock HTTP) | tests/unit/providers/test_search.py | 3.2.2 |

#### 3.3 Extractor Provider

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 3.3.1 | BaseExtractor 추상 인터페이스 | app/providers/extractor/base.py | 1.2.3 |
| 3.3.2 | TrafilaturaExtractor 구현 | app/providers/extractor/trafilatura_extractor.py | 3.3.1 |
| 3.3.3 | ReadabilityExtractor 구현 (fallback) | app/providers/extractor/readability_extractor.py | 3.3.1 |
| 3.3.4 | PlaywrightExtractor 구현 (최종 fallback) | app/providers/extractor/playwright_extractor.py | 3.3.1 |
| 3.3.5 | Extractor 체인 로직 | app/providers/extractor/chain.py | 3.3.2~3.3.4 |

---

### 4. 핵심 서비스 레이어

#### 4.1 Topic Service

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.1.1 | 주제 CRUD 로직 | app/services/topic_service.py | 2.2.1 |
| 4.1.2 | 주제 단위 테스트 (TC-T01~T04) | tests/unit/services/test_topic.py | 4.1.1 |

#### 4.2 Rule Engine

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.2.1 | classify_url 함수 구현 | app/services/rule_engine.py | 2.2.1 |
| 4.2.2 | 룰 CRUD 서비스 | app/services/rule_service.py | 2.2.1 |
| 4.2.3 | 룰 엔진 단위 테스트 (TC-R01~R05) | tests/unit/services/test_rule_engine.py | 4.2.1 |

#### 4.3 Query Planner

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.3.1 | 프롬프트 템플릿 설계 | app/services/query_planner.py | 3.1.1 |
| 4.3.2 | 구조화 출력 파싱 로직 | 위 동일 | 4.3.1 |
| 4.3.3 | 재시도 로직 (비JSON 응답 처리) | 위 동일 | 4.3.2 |
| 4.3.4 | Query Planner 단위 테스트 (TC-Q01~Q04) | tests/unit/services/test_query_planner.py | 4.3.3 |

#### 4.4 Search Service

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.4.1 | 검색 실행 + search_runs 기록 | app/services/search_service.py | 3.2.2, 2.2.2 |
| 4.4.2 | URL 중복 제거 로직 | 위 동일 | 4.4.1 |

#### 4.5 Fetch Service

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.5.1 | HTTP 요청 + raw 저장 로직 | app/services/fetch_service.py | 3.3.5 |
| 4.5.2 | 재시도 (최대 3회) 로직 | 위 동일 | 4.5.1 |

#### 4.6 Relevance Service

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.6.1 | 1차 규칙 기반 필터 구현 | app/services/relevance_service.py | 2.2.1 |
| 4.6.2 | 2차 LLM 의미 검증 프롬프트 + 파싱 | 위 동일 | 3.1.1 |
| 4.6.3 | 관련성 검증 단위 테스트 (TC-V01~V05) | tests/unit/services/test_relevance.py | 4.6.2 |

#### 4.7 Archive Service

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.7.1 | Document upsert + 버전 관리 로직 | app/services/archive_service.py | 2.2.3 |
| 4.7.2 | content_hash 기반 중복 방지 | 위 동일 | 4.7.1 |
| 4.7.3 | Archive tier 전환 로직 (Active→Warm→Cold) | 위 동일 | 4.7.1 |
| 4.7.4 | 문서 저장 통합 테스트 (TC-S01~S04) | tests/integration/test_archive.py | 4.7.2 |

#### 4.8 RAG Service

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.8.1 | 청킹 로직 구현 | app/services/rag_service.py | 2.2.4 |
| 4.8.2 | 임베딩 생성 + Qdrant 저장 | 위 동일 | 4.8.1 |
| 4.8.3 | 하이브리드 검색 (FTS5 + 벡터) | 위 동일 | 4.8.2 |
| 4.8.4 | RAG 답변 생성 (컨텍스트 조합 + LLM) | 위 동일 | 4.8.3 |
| 4.8.5 | RAG 단위·통합 테스트 (TC-I01~I03) | tests/integration/test_rag.py | 4.8.4 |

#### 4.9 Model Router

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.9.1 | capability 기반 모델 선택 로직 | app/services/model_router.py | 2.2.5 |
| 4.9.2 | 예산 체크 + fallback chain 로직 | 위 동일 | 4.9.1 |
| 4.9.3 | NoAvailableModelError 예외 처리 | 위 동일 | 4.9.2 |
| 4.9.4 | Model Router 단위 테스트 (TC-M01~M03) | tests/unit/services/test_model_router.py | 4.9.3 |

#### 4.10 Usage Service

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 4.10.1 | 토큰 사용량 기록 로직 | app/services/usage_service.py | 2.2.5 |
| 4.10.2 | 일일 리셋 로직 (Asia/Seoul) | 위 동일 | 4.10.1 |
| 4.10.3 | Usage Service 단위 테스트 (TC-M04~M05) | tests/unit/services/test_usage.py | 4.10.2 |

---

### 5. 수집 파이프라인 통합

#### 5.1 파이프라인 오케스트레이터

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 5.1.1 | 15단계 파이프라인 실행 흐름 구현 | app/core/pipeline.py | 4.1~4.8 전체 |
| 5.1.2 | 단계별 오류 처리 + 로그 기록 | 위 동일 | 5.1.1 |
| 5.1.3 | 파이프라인 통합 테스트 (전체 흐름) | tests/integration/test_pipeline.py | 5.1.2 |

#### 5.2 스케줄러

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 5.2.1 | APScheduler 기반 스케줄러 초기화 | app/scheduler/scheduler.py | 5.1.1 |
| 5.2.2 | 주제별 cron 잡 동적 등록 로직 | app/scheduler/jobs.py | 5.2.1 |
| 5.2.3 | 토큰 리셋 잡 등록 | 위 동일 | 5.2.1 |
| 5.2.4 | 아카이브 tier 전환 잡 등록 | 위 동일 | 5.2.1 |
| 5.2.5 | 스케줄러 통합 테스트 (TC-SC01~SC02) | tests/integration/test_scheduler.py | 5.2.2 |

---

### 6. API 레이어 (FastAPI)

#### 6.1 Topics API

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 6.1.1 | GET/POST/PUT/DELETE /topics 라우터 | app/api/routes/topics.py | 4.1.1 |
| 6.1.2 | POST /topics/{id}/run (즉시 실행) | 위 동일 | 5.1.1 |
| 6.1.3 | Topics API 테스트 (TC-API01~TC-API03 포함) | tests/api/test_topics.py | 6.1.1 |

#### 6.2 Rules API

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 6.2.1 | CRUD + POST /rules/test 라우터 | app/api/routes/rules.py | 4.2.2 |
| 6.2.2 | Rules API 테스트 (TC-R05) | tests/api/test_rules.py | 6.2.1 |

#### 6.3 Documents API

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 6.3.1 | GET /documents, /documents/{id}, /versions 라우터 | app/api/routes/documents.py | 4.7.1 |
| 6.3.2 | Documents API 테스트 (TC-S04) | tests/api/test_documents.py | 6.3.1 |

#### 6.4 RAG API

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 6.4.1 | POST /rag/query, GET /rag/chunks 라우터 | app/api/routes/rag.py | 4.8.4 |
| 6.4.2 | RAG API 테스트 (TC-I03) | tests/api/test_rag.py | 6.4.1 |

#### 6.5 Models API

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 6.5.1 | 모델 CRUD + 사용량 조회 라우터 | app/api/routes/models.py | 4.9.1 |
| 6.5.2 | POST /models/reset-usage 라우터 | 위 동일 | 4.10.2 |

---

### 7. 테스트 (통합 정비)

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 7.1.1 | conftest.py 픽스처 정비 (DB, topic, mock_llm) | tests/conftest.py | 2.2.6 |
| 7.1.2 | 단위 테스트 전체 실행 + 커버리지 80% 달성 | pytest 리포트 | 4.x 전체 |
| 7.2.1 | 통합 테스트 전체 실행 | pytest 리포트 | 5.x, 6.x 전체 |
| 7.3.1 | API 테스트 전체 실행 (TestClient) | pytest 리포트 | 6.x 전체 |

---

### 8. 배포 및 운영 준비

| 작업 ID | 작업명 | 산출물 | 선행 작업 |
|---------|--------|--------|-----------|
| 8.1.1 | .env.example 최종 정비 | .env.example | 6.x 전체 |
| 8.1.2 | config/settings.yaml 최종 정비 | settings.yaml | 6.x 전체 |
| 8.1.3 | main.py FastAPI 앱 + 스케줄러 시작점 | main.py | 5.2.1, 6.x |
| 8.1.4 | scripts/init_db.py 검증 | 초기화 스크립트 | 1.3.2 |
| 8.2.1 | 실제 Brave API + Ollama 환경 E2E 수동 검증 | E2E 체크리스트 | 8.1.x 전체 |
| 8.2.2 | 이슈 수정 및 재검증 | 수정 완료 | 8.2.1 |

---

## 작업 순서 요약 (Critical Path)

```
1.1 → 1.2 → 1.3
         ↓
       2.1 → 2.2
         ↓
3.1 ─┐  4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → 4.9 → 4.10
3.2 ─┤    ↓
3.3 ─┘  5.1 → 5.2
         ↓
       6.1 → 6.2 → 6.3 → 6.4 → 6.5
         ↓
       7.x → 8.x
```

**병렬 가능 작업**

- 3.1 / 3.2 / 3.3 (각 Provider): 동시 진행 가능
- 4.1 / 4.2 (Topic, Rule): 동시 진행 가능
- 4.9 / 4.10 (Router, Usage): 2.2.5 완료 후 동시 진행 가능
- 6.1 / 6.2 / 6.3 / 6.4 / 6.5: 해당 서비스 완료 후 병렬 가능

---

## 우선순위 분류

| 우선순위 | 작업 그룹 | 이유 |
|----------|-----------|------|
| P0 (Blocker) | 1.x, 2.x | 모든 기능의 기반 |
| P1 (핵심) | 3.1, 4.1~4.10, 5.1 | MVP 핵심 파이프라인 |
| P2 (중요) | 5.2, 6.x | 자동화 + 외부 접근 |
| P3 (완성) | 7.x, 8.x | 품질 보증 + 운영 준비 |
