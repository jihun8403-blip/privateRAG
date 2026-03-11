# TS — Test Strategy

**버전**: 1.0
**작성일**: 2026-03-11
**상태**: Draft

---

## 1. 테스트 목표

| 목표 | 설명 |
|------|------|
| 기능 정확성 | 각 서비스가 PRD 요구사항을 정확히 수행하는가 |
| 파이프라인 무결성 | 15단계 수집 파이프라인이 중간 실패 없이 완주되는가 |
| 모델 라우팅 신뢰성 | 예산 초과·오류 시 fallback이 정확히 동작하는가 |
| 데이터 일관성 | 버전 관리·아카이브 이력이 손실 없이 기록되는가 |
| 룰 엔진 정확성 | URL 분류(차단/우선/중립)가 명세와 일치하는가 |
| 회귀 안전성 | 기능 추가 시 기존 동작이 깨지지 않는가 |

---

## 2. 테스트 범위

### 2.1 In-Scope

- 모든 서비스 클래스 (unit)
- 파이프라인 전체 흐름 (integration)
- API 엔드포인트 입출력 (API)
- 모델 라우터 fallback 체인 (unit + integration)
- URL 룰 엔진 (unit)
- 관련성 검증 2단계 (unit + mock LLM)
- 스케줄러 트리거 (integration)
- DB 버전 관리 (integration)

### 2.2 Out-of-Scope (MVP)

- 실제 외부 API 호출 (E2E는 수동 검증)
- UI 브라우저 자동화
- 다중 사용자 시나리오
- 성능 부하 테스트 (2차 이후)

---

## 3. 테스트 레벨

### 3.1 단위 테스트 (Unit Test)

**대상**: 개별 함수·메서드·클래스

**도구**: pytest, pytest-asyncio

**커버리지 목표**: 80% 이상 (services/, providers/)

**Mock 전략**

| 대상 | Mock 방법 |
|------|-----------|
| LLM API 호출 | pytest-mock으로 LLMResponse 반환 고정 |
| 검색 API 호출 | SearchResult 목록 픽스처로 대체 |
| 파일 시스템 | tmp_path fixture 사용 |
| DB | SQLite in-memory (:memory:) |
| 시간 | freezegun으로 datetime 고정 |

### 3.2 통합 테스트 (Integration Test)

**대상**: 서비스 간 협력, DB 연동, 파이프라인 흐름

**환경**: SQLite in-memory + 실제 파일 I/O (tmp_path)

**핵심 시나리오**

1. 주제 등록 → 질의 생성 → 검색 → 필터링 → 저장 전체 흐름
2. 동일 URL 재수집 시 버전 생성 확인
3. 모델 예산 초과 시 fallback 모델로 전환
4. 토큰 사용량 일일 리셋 후 used_tokens_today = 0 확인

### 3.3 API 테스트

**도구**: pytest + httpx (TestClient)

**환경**: FastAPI TestClient, 테스트 DB

**검증 항목**

- 응답 HTTP 상태 코드
- 응답 스키마 (Pydantic 모델 일치)
- 입력 유효성 검사 (422 반환 확인)
- 인증 헤더 없는 요청 처리

### 3.4 수동 E2E 테스트

**주기**: 1차 MVP 완성 후, 2차 기능 추가 전

**대상**: 실제 Brave API + Ollama 환경에서 전체 파이프라인 1회 실행

---

## 4. 테스트 환경

### 4.1 로컬 개발 환경

```
OS: Windows 10
Python: 3.11+
DB: SQLite in-memory (테스트용)
LLM: Mock 또는 로컬 Ollama
검색 API: Mock (BraveAdapter stub)
벡터 DB: Mock 또는 로컬 Qdrant
```

### 4.2 CI 환경 (선택적)

```
GitHub Actions 또는 로컬 pre-commit hook
python -m pytest tests/ --cov=app --cov-report=term-missing
```

---

## 5. 테스트 데이터 전략

### 5.1 픽스처 원칙

- 모든 테스트는 독립적이어야 한다 (테스트 간 상태 공유 금지)
- DB는 각 테스트마다 새로 생성하고 종료 시 폐기
- 외부 API 응답은 `tests/fixtures/` JSON 파일로 관리

### 5.2 기본 픽스처

```python
# tests/conftest.py
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def sample_topic():
    return Topic(
        topic_id="t001",
        name="로컬 LLM 에이전트",
        description="온프레미스 LLM 에이전트 프레임워크 추적",
        must_include=["local llm", "agent"],
        must_exclude=["openai exclusive"],
        language=["ko", "en"],
        priority=8,
        schedule_cron="0 */6 * * *",
        enabled=True
    )

@pytest.fixture
def mock_llm_provider(mocker):
    provider = mocker.Mock(spec=BaseLLMProvider)
    provider.complete.return_value = LLMResponse(
        content='{"queries": [...]}',
        input_tokens=100,
        output_tokens=50,
        model_name="mock-model"
    )
    return provider
```

---

## 6. 테스트 자동화 실행

```bash
# 전체 테스트 실행
pytest tests/

# 커버리지 포함
pytest tests/ --cov=app --cov-report=html

# 단위 테스트만
pytest tests/unit/

# 통합 테스트만
pytest tests/integration/

# 특정 마커
pytest -m "not slow"
```

**pytest 마커 정의**

```ini
# pytest.ini
[pytest]
markers =
    unit: 단위 테스트
    integration: 통합 테스트
    api: API 엔드포인트 테스트
    slow: 실행 시간이 긴 테스트 (E2E 등)
```

---

## 7. 품질 기준

| 항목 | 기준 |
|------|------|
| 단위 테스트 커버리지 | 80% 이상 |
| 핵심 파이프라인 통합 테스트 | 15단계 전 구간 통과 |
| API 응답 스키마 | 100% Pydantic 검증 통과 |
| Fallback 시나리오 | 모든 실패 케이스 커버 |
| 회귀 테스트 | PR 병합 전 전체 테스트 통과 |

---

## 8. 결함 분류 기준

| 등급 | 설명 | 예시 |
|------|------|------|
| Critical | 데이터 손실, 파이프라인 중단 | 문서 저장 실패, 버전 충돌 |
| High | 핵심 기능 오동작 | fallback 미작동, relevance 점수 오류 |
| Medium | 부분 기능 오동작 | 요약 누락, 스케줄 지연 |
| Low | 사소한 오류 | 로그 메시지 오탈자 |

---

## 9. 테스트 책임

| 역할 | 책임 |
|------|------|
| 개발자 | 단위 테스트 작성 (기능 구현과 동시) |
| 개발자 | 통합 테스트 작성 (서비스 완성 시) |
| 개발자 | API 테스트 작성 (엔드포인트 완성 시) |
| 수동 검증 | E2E 시나리오 실행 (릴리스 전) |
