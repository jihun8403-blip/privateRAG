# PrivateRAG

**주제 중심 자동 수집·검증·검색 RAG 시스템**

관심 주제를 등록하면 웹에서 관련 문서를 자동 수집하고, 2단계 관련성 검증을 거쳐 로컬 RAG 인덱스에 저장합니다. 이후 자연어로 질문하면 수집한 문서 기반으로 답변을 생성합니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **주제 등록** | 이름, 설명, 키워드, 도메인 규칙, 수집 주기를 설정 |
| **자동 수집** | APScheduler cron 설정에 따라 Brave Search API로 URL 수집 |
| **관련성 검증** | 규칙 기반 1차 필터 → LLM 의미 검증 2단계 |
| **문서 버전 관리** | 동일 URL 내용 변경 시 버전 이력 보존 |
| **RAG 질의응답** | 벡터 검색(Qdrant) + LLM 답변 생성, 출처 표시 |
| **모델 라우팅** | capability/예산/우선순위 기반 자동 모델 선택, fallback 체인 |
| **온프레미스 우선** | Ollama 로컬 LLM 기본 사용, API LLM은 선택적 fallback |

---

## 아키텍처

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

### 15단계 수집 파이프라인

```
[1] topic load       → 주제 및 규칙 로드
[2] query generate   → LLM 기반 검색 쿼리 생성
[3] search           → Brave Search API 호출
[4] url filter       → 차단/우선 도메인 규칙 적용
[5] dedup            → URL 중복 제거
[6] fetch            → HTTP 수집 (도메인별 딜레이, 최대 동시 5개)
[7] extract          → 본문 추출 (trafilatura → readability → playwright)
[8] rule filter      → 키워드/길이 1차 필터
[9] llm check        → LLM 의미 관련성 검증 (score 0~1)
[10] normalize       → 본문 정제
[11] archive raw     → 원문 HTML 파일시스템 저장
[12] upsert          → DB 저장 및 버전 관리
[13] chunking        → 텍스트 청크 분할
[14] embedding       → sentence-transformers 임베딩 생성
[15] qdrant index    → 벡터 저장소 인덱싱
```

---

## 기술 스택

| 구분 | 선택 |
|------|------|
| 백엔드 프레임워크 | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.x (async) + aiosqlite |
| 데이터베이스 | SQLite (FTS5) → PostgreSQL 마이그레이션 가능 |
| 벡터 저장소 | Qdrant |
| 임베딩 | sentence-transformers (paraphrase-multilingual-mpnet-base-v2, 768차원) |
| 로컬 LLM | Ollama (qwen2.5:7b 권장, 한국어 강력) |
| API LLM | OpenAI, Anthropic (선택적 fallback) |
| 스케줄러 | APScheduler 3.10.x |
| 본문 추출 | trafilatura → readability-lxml → playwright |
| 설정 관리 | pydantic-settings (.env + YAML) |
| 테스트 | pytest + pytest-asyncio + pytest-mock + freezegun |

---

## 사전 요구사항

- Python 3.11 이상
- [Ollama](https://ollama.com) (로컬 LLM 사용 시)
- [Qdrant](https://qdrant.tech) (Docker 또는 Windows 바이너리)
- [Brave Search API 키](https://brave.com/search/api/) (자동 수집 사용 시)

---

## 설치 및 초기 설정

### 1. 저장소 클론 및 가상환경 생성

```bash
git clone <repo-url>
cd PrivateRAG

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -e ".[dev]"

# Playwright 브라우저 설치 (JS 렌더링 페이지 추출용)
playwright install chromium
```

### 3. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 필요한 값을 입력합니다.

```dotenv
# 검색 API (필수 — 자동 수집 사용 시)
BRAVE_API_KEY=your_brave_api_key

# Ollama (기본값 사용 가능)
OLLAMA_BASE_URL=http://127.0.0.1:11434

# API LLM (선택)
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 4. Ollama 모델 설치

```bash
# 한국어 성능이 좋은 qwen2.5:7b 권장
ollama pull qwen2.5:7b

# 경량 fallback 모델 (선택)
ollama pull llama3.2:3b
```

### 5. Qdrant 실행

```bash
# Docker 사용 시
docker run -d -p 6333:6333 qdrant/qdrant

# 또는 Windows 바이너리 직접 실행
# https://qdrant.tech/documentation/quick-start/
```

### 6. DB 및 초기 데이터 설정

```bash
python scripts/setup.py
```

이 스크립트는 다음을 자동으로 수행합니다.
- SQLite DB 테이블 생성
- Qdrant 컬렉션 생성
- 기본 LLM 모델 4종 등록 (Ollama qwen2.5:7b, llama3.2:3b, GPT-4o-mini, Claude Haiku)

---

## 서버 실행

```bash
# 개발 모드 (코드 변경 시 자동 재시작)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드
uvicorn main:app --host 0.0.0.0 --port 8000
```

서버 시작 후 API 문서를 확인합니다.
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- 헬스체크: `http://localhost:8000/health`

---

## 사용법

### 주제 등록

```bash
curl -X POST http://localhost:8000/topics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "로컬 LLM 에이전트",
    "description": "온프레미스 LLM 에이전트 프레임워크 동향 추적",
    "language": "ko,en",
    "priority": 8,
    "enabled": true,
    "schedule_cron": "0 */6 * * *",
    "relevance_threshold": 0.6,
    "must_include": ["local llm", "agent"],
    "must_exclude": ["openai exclusive"],
    "rules": [
      {
        "rule_type": "preferred_domain",
        "pattern": "github\\.com",
        "is_regex": true
      },
      {
        "rule_type": "blocked_domain",
        "pattern": "pinterest\\.com",
        "is_regex": true
      }
    ]
  }'
```

### 즉시 수집 실행

```bash
# {topic_id}는 주제 등록 응답에서 확인
curl -X POST http://localhost:8000/topics/{topic_id}/run
```

### 자연어 질의응답

```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "로컬 LLM 에이전트 프레임워크의 주요 특징은?",
    "topic_ids": ["{topic_id}"],
    "top_k": 5
  }'
```

응답 예시:
```json
{
  "answer": "로컬 LLM 에이전트 프레임워크의 주요 특징으로는...",
  "sources": [
    {
      "url": "https://github.com/...",
      "title": "Local LLM Agent Framework",
      "collected_at": "2026-03-11T09:00:00",
      "relevance_score": 0.92
    }
  ],
  "model_used": "qwen2.5:7b"
}
```

### 도메인 룰 테스트

```bash
curl -X POST http://localhost:8000/rules/test \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/owner/repo",
    "topic_id": "{topic_id}"
  }'
```

### 문서 버전 이력 조회

```bash
curl http://localhost:8000/documents/{doc_id}/versions
```

### 모델 토큰 사용량 조회

```bash
curl http://localhost:8000/models/{model_id}/usage
```

### 토큰 사용량 수동 초기화

```bash
curl -X POST http://localhost:8000/models/reset-usage
```

---

## API 엔드포인트 목록

### Topics

| Method | Path | 설명 |
|--------|------|------|
| GET | `/topics` | 주제 목록 (우선순위 오름차순) |
| POST | `/topics` | 주제 생성 |
| GET | `/topics/{id}` | 주제 상세 |
| PUT | `/topics/{id}` | 주제 수정 |
| DELETE | `/topics/{id}` | 주제 삭제 |
| POST | `/topics/{id}/run` | 즉시 수집 실행 |

### Rules

| Method | Path | 설명 |
|--------|------|------|
| GET | `/topics/{id}/rules` | 룰 목록 |
| POST | `/topics/{id}/rules` | 룰 생성 |
| PUT | `/rules/{rule_id}` | 룰 수정 |
| DELETE | `/rules/{rule_id}` | 룰 삭제 |
| POST | `/rules/test` | URL 룰 매칭 테스트 |

### Documents

| Method | Path | 설명 |
|--------|------|------|
| GET | `/documents` | 문서 목록 (주제/티어 필터) |
| GET | `/documents/{id}` | 문서 상세 |
| GET | `/documents/{id}/versions` | 버전 이력 |
| GET | `/documents/{id}/versions/{no}` | 특정 버전 |

### RAG

| Method | Path | 설명 |
|--------|------|------|
| POST | `/rag/query` | 자연어 질의응답 |
| GET | `/rag/chunks` | 청크 유사도 검색 |

### Models

| Method | Path | 설명 |
|--------|------|------|
| GET | `/models` | 모델 목록 |
| POST | `/models` | 모델 등록 |
| PUT | `/models/{id}` | 모델 수정 |
| GET | `/models/{id}/usage` | 사용량 요약 |
| GET | `/models/{id}/usage/logs` | 사용 로그 |
| POST | `/models/reset-usage` | 토큰 수동 초기화 |

---

## 프로젝트 구조

```
project/
├── app/
│   ├── api/
│   │   ├── routes/          # FastAPI 라우터 (topics, rules, documents, rag, models)
│   │   ├── schemas/         # Pydantic v2 Request/Response DTO
│   │   └── deps.py          # 의존성 주입 (DB 세션 등)
│   ├── core/
│   │   ├── config.py        # 설정 관리 (pydantic-settings)
│   │   ├── logging.py       # structlog 구조화 로깅
│   │   ├── pipeline.py      # 15단계 수집 파이프라인
│   │   └── app_state.py     # 전역 Provider 레지스트리
│   ├── db/
│   │   ├── base.py          # DeclarativeBase + TimestampMixin
│   │   ├── session.py       # 비동기 엔진 및 세션 팩토리
│   │   └── migrations/      # Alembic 마이그레이션
│   ├── models/              # SQLAlchemy ORM 모델 (10종)
│   ├── services/            # 비즈니스 로직 서비스 (10종)
│   ├── providers/
│   │   ├── llm/             # LLM 어댑터 (Ollama, OpenAI, Anthropic)
│   │   ├── search/          # 검색 어댑터 (Brave)
│   │   └── extractor/       # 본문 추출기 + fallback 체인
│   └── scheduler/           # APScheduler 잡 정의
├── data/
│   ├── raw/YYYY/MM/DD/      # 원문 HTML 보관
│   ├── normalized/          # 정제본
│   └── archive/             # 아카이브
├── tests/
│   ├── conftest.py          # 공통 픽스처 (in-memory DB, Mock LLM)
│   ├── unit/services/       # 서비스 단위 테스트
│   ├── integration/         # 통합 테스트
│   └── api/                 # API 엔드포인트 테스트
├── scripts/
│   ├── setup.py             # 초기 설정 스크립트
│   └── seed_models.py       # 기본 모델 데이터 시드
├── config/
│   └── settings.yaml        # 기본 설정값
├── .env.example             # 환경변수 예시
├── alembic.ini              # Alembic 마이그레이션 설정
├── pyproject.toml           # 패키지 의존성 및 도구 설정
└── main.py                  # FastAPI 앱 진입점
```

---

## 테스트

```bash
# 전체 테스트 실행
pytest tests/

# 커버리지 포함
pytest tests/ --cov=app --cov-report=term-missing

# 단위 테스트만
pytest tests/unit/ -v

# 통합 테스트만
pytest tests/integration/ -v

# API 테스트만
pytest tests/api/ -v

# 느린 테스트 제외
pytest -m "not slow"
```

**커버리지 목표**: 80% 이상 (services/, providers/)

---

## 설정 상세

### config/settings.yaml

```yaml
database:
  url: "sqlite+aiosqlite:///./data/privaterag.db"

qdrant:
  host: "localhost"
  port: 6333
  collection: "privaterag"

embedding:
  model: "paraphrase-multilingual-mpnet-base-v2"
  dimension: 768

relevance:
  default_threshold: 0.6   # 관련성 점수 기본 임계값
  min_text_length: 200      # 최소 본문 길이 (자)

chunking:
  chunk_size: 400           # 청크 크기 (자)
  chunk_overlap: 50         # 청크 겹침

archive:
  warm_after_days: 90       # active → warm 전환 기준일
  cold_after_days: 365      # warm → cold 전환 기준일
```

### 스케줄 cron 예시

| cron | 의미 |
|------|------|
| `0 */6 * * *` | 6시간마다 (기본값) |
| `0 9 * * *` | 매일 오전 9시 |
| `0 9 * * 1` | 매주 월요일 오전 9시 |
| `30 8,20 * * *` | 매일 오전 8:30, 오후 8:30 |

### rule_type 종류

| rule_type | 설명 |
|-----------|------|
| `preferred_domain` | 선호 도메인 (검색 쿼리에 site: 포함) |
| `blocked_domain` | 차단 도메인 |
| `preferred_url` | 선호 URL 패턴 |
| `blocked_url` | 차단 URL 패턴 |

> 적용 우선순위: `blocked_url` > `blocked_domain` > `preferred_url` > `preferred_domain`

---

## 모델 관리

### 새 Ollama 모델 추가

```bash
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model_name": "gemma3:12b",
    "capability_tags": ["answer"],
    "daily_budget_tokens": 999999999,
    "priority": 3
  }'
```

### capability_tags 종류

| 태그 | 용도 |
|------|------|
| `query_gen` | 검색 쿼리 자동 생성 |
| `relevance_check` | 문서 관련성 검증 |
| `answer` | RAG 최종 답변 생성 |

---

## 문제 해결

**Ollama 연결 실패**
```bash
# Ollama 서비스 상태 확인
ollama list
# 기본 URL이 127.0.0.1인지 확인 (localhost 대신 사용 권장)
```

**Qdrant 연결 실패**
```bash
# Docker 컨테이너 상태 확인
docker ps | grep qdrant
# 포트 확인
curl http://localhost:6333/health
```

**임베딩 모델 다운로드 오류**
```bash
# 수동 다운로드
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')"
```

**Windows에서 Playwright 오류**
```bash
# 브라우저 재설치
playwright install --with-deps chromium
```

---

## 라이선스

MIT License
