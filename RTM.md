# RTM — Requirement Traceability Matrix

**버전**: 1.0
**작성일**: 2026-03-11
**상태**: Draft

---

## 범례

| 기호 | 의미 |
|------|------|
| ✅ | 테스트 케이스 존재, 커버됨 |
| 🔲 | 테스트 케이스 미작성 (향후 추가 필요) |
| N/A | 테스트 불가 (환경 제약, 수동 검증) |

---

## 1. 기능 요구사항 RTM

| 요구사항 ID | 요구사항 설명 | 설계 참조 (SDS) | 테스트 케이스 | 상태 |
|------------|--------------|-----------------|---------------|------|
| **FR-T01** | 주제 CRUD + 비활성화 | SDS §4 topic_service | TC-T01, TC-T02 | ✅ |
| **FR-T02** | 주제 필드 전체 포함 (이름, 설명, cron 등) | SDS §3.1 topics 스키마 | TC-T01 | ✅ |
| **FR-T03** | 주제별 N개 도메인 룰 등록 | SDS §3.2 topic_rules | TC-T04 | ✅ |
| **FR-T04** | 주제 우선순위 정렬 조회 | SDS §4.1 | TC-T03 | ✅ |
| **FR-Q01** | LLM 기반 복수 검색 질의 자동 생성 | SDS §4.1 QueryPlanner | TC-Q01 | ✅ |
| **FR-Q02** | 질의 결과 구조화 (query/intent/language) | SDS §4.1 출력 스키마 | TC-Q01, TC-Q02 | ✅ |
| **FR-Q03** | 한국어/영어 질의 모두 생성 | SDS §4.1 | TC-Q02 | ✅ |
| **FR-Q04** | preferred_domain 기반 site: 질의 생성 | SDS §4.1 | TC-Q03 | ✅ |
| **FR-Q05** | 생성 질의 DB 저장 + 만료일 관리 | SDS §3.3 search_queries | 🔲 TC-Q05 | 🔲 |
| **FR-R01** | 검색 API 호출로 URL 수집 | SDS §5.2 SearchProvider | 🔲 TC-R10 | 🔲 |
| **FR-R02** | URL/도메인 regex 룰 적용 | SDS §4.3 Rule Engine | TC-R01~TC-R04 | ✅ |
| **FR-R03** | URL 중복 제거 | SDS §4.5 파이프라인 [5] | 🔲 TC-R11 | 🔲 |
| **FR-R04** | 본문 추출 (3단계 fallback) | SDS §5.3 Extractor | 🔲 TC-R12 | 🔲 |
| **FR-R05** | 수집 실행 이력 기록 | SDS §3.4 search_runs | 🔲 TC-R13 | 🔲 |
| **FR-R06** | 검색 제공자 플러그인 추가 가능 | SDS §5.2 BaseSearchProvider | 🔲 TC-R14 | 🔲 |
| **FR-V01** | 1차 규칙 기반 필터 (키워드/길이) | SDS §4.4 | TC-V01~TC-V02, TC-V05 | ✅ |
| **FR-V02** | 2차 LLM 의미 검증 (score + reason) | SDS §4.4 | TC-V03, TC-V04 | ✅ |
| **FR-V03** | relevance_score 임계값 주제별 설정 | SDS §3.1 (relevance_threshold) | TC-V03, TC-V04 | ✅ |
| **FR-V04** | 2차 검증 모델 자동 선택 | SDS §4.2 ModelRouter | TC-M01 | ✅ |
| **FR-S01** | 원문 HTML 파일 시스템 보관 | SDS §2 data/raw/ | 🔲 TC-S10 | 🔲 |
| **FR-S02** | 정제본/요약/메타 DB 저장 | SDS §3.6 documents | TC-S01 | ✅ |
| **FR-S03** | 동일 URL 내용 변경 시 신규 버전 생성 | SDS §3.7 document_versions | TC-S02, TC-S04 | ✅ |
| **FR-S04** | content_hash 중복 방지 | SDS §3.5 | TC-S03 | ✅ |
| **FR-I01** | 청크 분할 + 토큰 수 기록 | SDS §3.8 chunks | TC-I01 | ✅ |
| **FR-I02** | 임베딩 생성 + 벡터 저장소 저장 | SDS §4.5 파이프라인 [14] | TC-I02 | ✅ |
| **FR-I03** | 임베딩 모델 변경 시 재임베딩 | SDS §3.8 embedding_status | 🔲 TC-I10 | 🔲 |
| **FR-I04** | FTS5 + 벡터 하이브리드 검색 | SDS §6.4 RAG API | 🔲 TC-I11 | 🔲 |
| **FR-A01** | 자연어 질의에 RAG 답변 생성 | SDS §6.4 | TC-I03 | ✅ |
| **FR-A02** | 답변에 출처(URL, 제목, 수집일) 포함 | SDS §6.4 | TC-I03 | ✅ |
| **FR-A03** | 답변 생성 모델 사용자 선택 | SDS §4.2 ModelRouter | 🔲 TC-A10 | 🔲 |
| **FR-M01** | 모델 속성 (provider/capability/예산 등) | SDS §3.9 model_registry | TC-M01 | ✅ |
| **FR-M02** | task_type + capability 기반 자동 선택 | SDS §4.2 | TC-M01, TC-M02 | ✅ |
| **FR-M03** | 예산 초과/오류 시 fallback 전환 | SDS §4.2 | TC-M02, TC-M03 | ✅ |
| **FR-M04** | 토큰 사용량 일일 리셋 (Asia/Seoul) | SDS §7 스케줄러 | TC-M04 | ✅ |
| **FR-M05** | 모델별 사용량·비용 기록 | SDS §3.10 model_usage_logs | TC-M05 | ✅ |
| **FR-SC01** | 주제별 cron 수집 파이프라인 자동 실행 | SDS §7 | TC-SC01 | ✅ |
| **FR-SC02** | 토큰 일일 초기화 스케줄 | SDS §7 | TC-M04 | ✅ |
| **FR-SC03** | 아카이브 tier 전환 스케줄 | SDS §7 아카이브 기준 | 🔲 TC-SC10 | 🔲 |
| **FR-D01** | 4종 regex 룰 CRUD | SDS §6.2 Rules API | TC-T04 | ✅ |
| **FR-D02** | 차단 우선 룰 적용 순서 | SDS §4.3 | TC-R01~TC-R04 | ✅ |
| **FR-D03** | URL 룰 테스트 기능 | SDS §6.2 POST /rules/test | TC-R05 | ✅ |

---

## 2. 비기능 요구사항 RTM

| 요구사항 ID | 요구사항 설명 | 검증 방법 | 테스트 케이스 | 상태 |
|------------|--------------|-----------|---------------|------|
| **NFR-01** | 단일 주제 수집 파이프라인 10분 이내 | 실행 시간 측정 (E2E) | N/A (수동) | N/A |
| **NFR-02** | 검색·LLM 제공자 코드 수정 없이 추가 | BaseProvider 구현체 추가 테스트 | 🔲 TC-NFR02 | 🔲 |
| **NFR-03** | SQLite→PostgreSQL 마이그레이션 가능 | ORM 추상화 확인 (코드 리뷰) | N/A (코드 리뷰) | N/A |
| **NFR-04** | API 키 환경변수·시크릿 파일 관리 | 설정 로드 단위 테스트 | 🔲 TC-NFR04 | 🔲 |
| **NFR-05** | 외부 API 실패 시 최대 3회 재시도 | Mock 실패 주입 후 재시도 횟수 확인 | TC-Q04 (부분) | ✅ |
| **NFR-06** | 파이프라인 전 단계 실행 로그 기록 | DB search_runs·usage_logs 확인 | TC-M05, TC-R05 | ✅ |

---

## 3. 미작성 테스트 케이스 목록 (향후 추가)

| TC ID | 대상 요구사항 | 설명 |
|-------|--------------|------|
| TC-Q05 | FR-Q05 | 생성 질의 만료일 기준 필터링 |
| TC-R10 | FR-R01 | BraveAdapter 검색 결과 파싱 |
| TC-R11 | FR-R03 | URL 중복 제거 로직 |
| TC-R12 | FR-R04 | trafilatura→readability→playwright fallback |
| TC-R13 | FR-R05 | search_runs 이력 기록 |
| TC-R14 | FR-R06 | 새 SearchProvider 구현체 등록 |
| TC-I10 | FR-I03 | 임베딩 모델 변경 후 재임베딩 트리거 |
| TC-I11 | FR-I04 | FTS5 + 벡터 하이브리드 검색 결과 병합 |
| TC-A10 | FR-A03 | 답변 생성 모델 파라미터 전달 |
| TC-S10 | FR-S01 | 원문 파일 날짜별 디렉터리 저장 |
| TC-SC10 | FR-SC03 | 90일/365일 기준 tier 전환 |
| TC-NFR02 | NFR-02 | 새 Provider 추가 후 기존 파이프라인 무결성 |
| TC-NFR04 | NFR-04 | API 키 누락 시 명확한 오류 메시지 |

---

## 4. 커버리지 요약

| 분류 | 전체 요구사항 | 테스트 케이스 작성 완료 | 미작성 | 커버율 |
|------|-------------|------------------------|--------|--------|
| 기능 (FR) | 38 | 25 | 13 | 66% |
| 비기능 (NFR) | 6 | 3 | 3 | 50% |
| **합계** | **44** | **28** | **16** | **64%** |

> MVP 1차 출시 전 목표 커버율: **80% 이상**
