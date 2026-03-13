# PrivateRAG 작업 히스토리

---

## 2026-03-11

### 로그 한글 인코딩 문제
- **증상**: 로그 파일에 한글이 `\uc` 이스케이프 시퀀스로 출력됨
- **원인**: structlog `JSONRenderer`의 `ensure_ascii=True` 기본값
- **조치**: `app/core/logging.py` `JSONRenderer`에 `ensure_ascii=False` 추가 (미적용 상태로 세션 종료)

### LLM 쿼리 생성 파싱 실패 (qwen3.5:4b)
- **증상**: `output_tokens=1024`이지만 응답 내용이 비어 JSON 파싱 실패
- **원인**: qwen3 thinking 모델이 `<think>` 블록으로 최대 토큰을 소진 후 실제 응답 생성 불가
- **조치**: 모델을 `gemma3:4b`(non-thinking)로 교체, `/no_think` 지시어 추가

### Brave Search API 429 에러
- **증상**: 연속 검색 쿼리 실행 시 429 Too Many Requests
- **원인**: 쿼리 간 딜레이 없음
- **조치**: `app/services/search_service.py`에 쿼리 간 `asyncio.sleep(1.5)` 추가

### relevance_check 모델 없음 에러 (NoAvailableModelError)
- **증상**: 관련성 검증 단계에서 `NoAvailableModelError` 발생
- **원인**: DB 모델에 `relevance_check` capability 태그 미설정
- **조치**:
  - `app/services/relevance_service.py`: `NoAvailableModelError` catch → `is_relevant=True` fallback
  - `main.py`: 앱 시작 시 활성 모델에 `relevance_check` capability 자동 마이그레이션

### Playwright NotImplementedError (Windows)
- **증상**: 본문 추출 시 `NotImplementedError` 발생
- **원인**: Windows SelectorEventLoop에서 subprocess 미지원
- **조치**:
  - `app/providers/extractor/playwright_extractor.py`: `except NotImplementedError` 명시적 처리
  - 실행 방법을 `uvicorn main:app` → `python main.py`로 변경 (ProactorEventLoop 사용)

### 추출기 실패 메시지 개선
- **증상**: 모든 추출기 실패 시 마지막 에러만 표시
- **조치**: `app/providers/extractor/chain.py`에서 모든 추출기 에러를 수집 후 ` | ` 구분자로 합쳐 표시

### Google Gemini 어댑터 추가
- **조치**:
  - `app/providers/llm/google_adapter.py` 신규 생성 (OpenAI 호환 엔드포인트 사용)
  - `main.py` lifespan에 Google/Gemini provider 등록 로직 추가
  - `app/api/routes/models.py` `_try_register_provider()`에 Google 케이스 추가

### Qdrant 인덱싱 실패 (qdrant-client 1.17.0 protobuf 버그)
- **증상**: `unsupported operand type(s) for |: 'EnumTypeWrapper' and 'NoneType'`
- **원인**: qdrant-client 1.17.0 gRPC 스텁이 protobuf `EnumTypeWrapper`에 `|` 연산자 사용
- **조치**:
  - `main.py`: `QdrantClient(prefer_grpc=False)`, `field_schema="keyword"` (문자열)
  - `app/services/rag_service.py`: `QdrantClient(prefer_grpc=False)`, `vector=vector.tolist()`

---

## 2026-03-12

### 토큰 사용량 미반영 문제
- **증상**: LLM 호출 후 `used_tokens_today`가 변경되지 않음
- **원인**: `UsageService.log_usage()` 및 `ModelRouter.record_usage()`가 정의만 되어 있고 실제 호출 없음
- **조치**:
  - `app/services/query_planner.py`: `_call_with_retry()` 반환 타입을 `tuple[QueryPlanResult, int, int]`으로 변경, `generate_queries()`에서 `router.record_usage()` 호출
  - `app/services/relevance_service.py`: `select_model()` 반환 model 보존, LLM 성공 후 `router.record_usage()` 호출

### Qdrant 인덱싱 계속 실패 (EnumTypeWrapper 근본 원인)
- **증상**: `prefer_grpc=False` 적용 후에도 동일 에러 지속
- **원인**: `qdrant_client/__init__.py`가 `AsyncQdrantClient` import 시 `grpc_uploader.py` 로드 → `update_mode: grpc.UpdateMode | None` 어노테이션 평가 시 `TypeError` 발생. 모든 import 경로에서 동일하게 실패
  - qdrant-client 다운그레이드 시도 → `google-ai-generativelanguage`의 `protobuf<5.0` 요구로 버전 충돌
- **조치**:
  - `.venv/Lib/site-packages/qdrant_client/uploader/grpc_uploader.py` 상단에 `from __future__ import annotations` 추가 (어노테이션 지연 평가)
  - `app/services/rag_service.py`: `vector.tolist()` → `vector` (`_sync_embed`가 이미 `.tolist()` 반환하므로 중복 제거)

### 모델별 호출 간격(초) 설정 기능 추가
- **기능**: 모델별 연속 호출 최소 대기 시간 설정 (API rate limit 방지)
- **조치**:
  - `app/models/model_registry.py`: `call_interval_seconds: Mapped[float]` 컬럼 추가 (기본값 0.0)
  - `app/api/schemas/model_registry.py`: `ModelRegistryBase`, `ModelRegistryUpdate`에 필드 추가
  - `main.py`: DB 마이그레이션 (`ALTER TABLE ... ADD COLUMN call_interval_seconds REAL DEFAULT 0.0`)
  - `app/services/model_router.py`:
    - `_last_called: dict[str, float]` 클래스 변수 (앱 전역 공유)
    - `select_model()`: 간격 미경과 시 `asyncio.sleep(wait)` 후 진행, info 레벨 로그
    - `record_usage()`: 호출 완료 시 `_last_called` 타임스탬프 갱신
  - `service/web/src/types/api.ts`: `call_interval_seconds` 필드 추가
  - `service/web/src/app/models/page.tsx`: 폼 입력 필드 및 카드 표시 추가

### 챗봇 500 에러 (provider 이름 불일치)
- **증상**: `/rag/query` 호출 시 `task_type=answer: 예산/health_check 통과 모델 없음`으로 500 반환
- **원인**: DB에 provider가 `"gemini"`로 저장되어 있으나 등록 코드에서 `"google"`로 비교 → `GoogleAdapter` 미등록 → `Provider 미등록 스킵` → `NoAvailableModelError`
- **조치**:
  - `main.py`: `== "google"` → `in ("google", "gemini")`
  - `app/api/routes/models.py`: `== "google"` → `in ("google", "gemini")`
  - `app/api/schemas/model_registry.py`: provider 패턴에 `google` 추가
  - `service/web/src/types/api.ts`: `Provider` 타입에 `"google"` 추가
  - `service/web/src/app/models/page.tsx`: `PROVIDER_COLORS`, `MODEL_SUGGESTIONS`에 `"google"` 항목 추가

---

## 2026-03-13

### 챗봇 채팅 이력 영구 저장
- **기능**: 페이지 이동·새로고침 후에도 대화 이력 유지, 사용자가 명시적으로 클리어하기 전까지 보존
- **조치**:
  - `service/web/src/app/chat/page.tsx`:
    - `loadMessages()` 함수 추가 — `localStorage("chat_history")` 복원 (`Date` 문자열 → `Date` 객체 변환)
    - `useState` lazy initializer로 초기값 로드
    - `useEffect([messages])` — 메시지 변경 시 localStorage 저장
    - `handleClear()` + "대화 초기화" 버튼 (메시지가 있을 때만 헤더에 표시)

### 문서 상세 페이지 — AI 요약 기능 추가
- **기능**: 문서 URL을 재수집·추출하여 LLM으로 구조화 Markdown 요약 생성, Qdrant 기반 관련 문서 TOP5 표시
- **조치**:
  - `app/services/summary_service.py` **신규 생성**
    - `SummaryService.generate()`: FetchService → ExtractionPipeline → LLM(`capability=answer`, `max_tokens=3000`) → Qdrant 관련 문서 검색 → `doc.summary` DB 저장
    - `_find_related()`: 문서 제목+본문 임베딩 → Qdrant 검색(limit=30) → 현재 문서 제외 → doc_id별 최고 점수 dedupe → 상위 5개
    - `_build_related_section()`: 관련 문서 Markdown 테이블 생성 후 LLM 응답에 appending
    - LLM 프롬프트: 핵심 요약 / 배경 / 대상 독자 / 의미·영향 / 섹션별 요약 / 실무 적용 방안 / 키워드 7개 섹션 구조화
  - `app/api/schemas/document.py`: `RelatedDocItem`, `DocSummaryResponse` 스키마 추가
  - `app/api/routes/documents.py`: `POST /documents/{doc_id}/summary` 엔드포인트 추가
  - `service/web/src/types/api.ts`: `RelatedDocItem`, `DocSummaryResponse` 타입 추가
  - `service/web/src/app/documents/[id]/page.tsx`:
    - "요약 실행" / "재요약" 버튼 헤더 우측 배치 (로딩 중 스피너)
    - AI 요약 Card를 메타데이터 Card **위**에 삽입 (`react-markdown` + `remark-gfm` 렌더링)
    - 기존 `doc.summary`가 있으면 로드 시 즉시 표시

### 문서 목록 AI 요약 여부 표시
- **기능**: 문서 목록에서 AI 요약이 생성된 문서를 시각적으로 구별
- **조치**:
  - `service/web/src/app/documents/page.tsx`: 제목 옆에 `Sparkles` 아이콘 표시 (`doc.summary` truthy일 때), hover 시 "AI 요약 있음" 툴팁
