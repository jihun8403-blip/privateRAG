# TCC — Test Case Specification

**버전**: 1.0
**작성일**: 2026-03-11
**상태**: Draft

---

## 1. 주제 관리 (Topic Service)

### TC-T01. 주제 정상 생성

| 항목 | 내용 |
|------|------|
| **ID** | TC-T01 |
| **분류** | Unit / Integration |
| **대상** | `topic_service.create_topic()` |
| **전제조건** | DB 초기화 완료 |
| **입력** | name="로컬 LLM 에이전트", description="...", priority=8, enabled=True, schedule_cron="0 */6 * * *" |
| **실행** | `topic_service.create_topic(topic_data)` |
| **기대결과** | DB에 topic 레코드 1건 삽입, topic_id 반환, created_at 자동 설정 |
| **연결 요구사항** | FR-T01, FR-T02 |

### TC-T02. 주제 비활성화

| 항목 | 내용 |
|------|------|
| **ID** | TC-T02 |
| **입력** | 기존 topic_id, enabled=False |
| **실행** | `topic_service.update_topic(id, {"enabled": False})` |
| **기대결과** | DB enabled=False, 스케줄러가 해당 주제 실행 안 함 |
| **연결 요구사항** | FR-T01 |

### TC-T03. 우선순위 정렬 조회

| 항목 | 내용 |
|------|------|
| **ID** | TC-T03 |
| **전제조건** | 주제 3건 등록 (priority=1, 5, 10) |
| **실행** | `topic_service.list_topics()` |
| **기대결과** | priority 오름차순 정렬 반환 |
| **연결 요구사항** | FR-T04 |

### TC-T04. 도메인 룰 등록

| 항목 | 내용 |
|------|------|
| **ID** | TC-T04 |
| **입력** | topic_id, rule_type="preferred_domain", pattern="github\\.com", is_regex=True |
| **실행** | `topic_service.add_rule(rule_data)` |
| **기대결과** | topic_rules 테이블에 1건 삽입 |
| **연결 요구사항** | FR-T03, FR-D01 |

---

## 2. URL 룰 엔진 (Rule Engine)

### TC-R01. 차단 URL 판별

| 항목 | 내용 |
|------|------|
| **ID** | TC-R01 |
| **전제조건** | blocked_url 룰: `.*pinterest.*` |
| **입력** | url="https://www.pinterest.com/some/page" |
| **실행** | `classify_url(url, rules)` |
| **기대결과** | "blocked" 반환 |
| **연결 요구사항** | FR-D01, FR-D02 |

### TC-R02. 우선 도메인 판별

| 항목 | 내용 |
|------|------|
| **ID** | TC-R02 |
| **전제조건** | preferred_domain 룰: `github\\.com` |
| **입력** | url="https://github.com/owner/repo" |
| **실행** | `classify_url(url, rules)` |
| **기대결과** | "preferred" 반환 |
| **연결 요구사항** | FR-D02 |

### TC-R03. 차단이 우선 도메인보다 우선함

| 항목 | 내용 |
|------|------|
| **ID** | TC-R03 |
| **전제조건** | blocked_domain: `github\\.com`, preferred_domain: `github\\.com` 동시 등록 |
| **입력** | url="https://github.com/test" |
| **실행** | `classify_url(url, rules)` |
| **기대결과** | "blocked" 반환 (차단 우선 원칙) |
| **연결 요구사항** | FR-D02 |

### TC-R04. 중립 URL 판별

| 항목 | 내용 |
|------|------|
| **ID** | TC-R04 |
| **입력** | url="https://example.com/article" (어떤 룰도 매칭 안 됨) |
| **실행** | `classify_url(url, rules)` |
| **기대결과** | "neutral" 반환 |
| **연결 요구사항** | FR-D02 |

### TC-R05. 룰 테스트 API

| 항목 | 내용 |
|------|------|
| **ID** | TC-R05 |
| **입력** | POST /rules/test { "url": "https://github.com/x", "topic_id": "t001" } |
| **실행** | API 호출 |
| **기대결과** | 200 OK, { "result": "preferred", "matched_rule": "github\\.com" } |
| **연결 요구사항** | FR-D03 |

---

## 3. 검색 질의 생성 (Query Planner)

### TC-Q01. 정상 질의 생성

| 항목 | 내용 |
|------|------|
| **ID** | TC-Q01 |
| **전제조건** | Mock LLM이 구조화된 JSON 반환 |
| **입력** | sample_topic (로컬 LLM 에이전트 주제) |
| **실행** | `query_planner.generate_queries(topic)` |
| **기대결과** | queries 리스트 반환, 각 항목에 query/intent/language 포함 |
| **연결 요구사항** | FR-Q01, FR-Q02 |

### TC-Q02. 한국어·영어 질의 모두 생성

| 항목 | 내용 |
|------|------|
| **ID** | TC-Q02 |
| **실행** | `query_planner.generate_queries(topic)` |
| **기대결과** | language="ko" 쿼리 1개 이상 + language="en" 쿼리 1개 이상 |
| **연결 요구사항** | FR-Q03 |

### TC-Q03. preferred_domain 질의 생성

| 항목 | 내용 |
|------|------|
| **ID** | TC-Q03 |
| **전제조건** | 주제에 preferred_domain_regex: ["github\\.com"] 등록 |
| **실행** | `query_planner.generate_queries(topic)` |
| **기대결과** | intent="preferred_domain" 쿼리 포함 (site:github.com ...) |
| **연결 요구사항** | FR-Q04 |

### TC-Q04. LLM 비정상 응답 시 재시도

| 항목 | 내용 |
|------|------|
| **ID** | TC-Q04 |
| **전제조건** | Mock LLM이 첫 호출에 비JSON 반환, 2회차에 정상 반환 |
| **실행** | `query_planner.generate_queries(topic)` |
| **기대결과** | 재시도 후 정상 결과 반환 |
| **연결 요구사항** | NFR-05 |

---

## 4. 관련성 검증 (Relevance Validator)

### TC-V01. 1차 필수 키워드 미포함 → 폐기

| 항목 | 내용 |
|------|------|
| **ID** | TC-V01 |
| **전제조건** | must_include=["local llm", "agent"] |
| **입력** | 본문에 "local llm" 없음 |
| **실행** | `relevance_service.rule_filter(doc, topic)` |
| **기대결과** | False 반환, 2차 LLM 검사 미진행 |
| **연결 요구사항** | FR-V01 |

### TC-V02. 1차 제외 키워드 포함 → 폐기

| 항목 | 내용 |
|------|------|
| **ID** | TC-V02 |
| **전제조건** | must_exclude=["openai exclusive"] |
| **입력** | 본문에 "openai exclusive" 포함 |
| **실행** | `relevance_service.rule_filter(doc, topic)` |
| **기대결과** | False 반환 |
| **연결 요구사항** | FR-V01 |

### TC-V03. 1차 통과 → 2차 LLM 점수 임계값 이상 → 저장

| 항목 | 내용 |
|------|------|
| **ID** | TC-V03 |
| **전제조건** | Mock LLM이 { "is_relevant": true, "score": 0.87, "reason": "..." } 반환 |
| **입력** | 1차 통과한 문서, topic.relevance_threshold=0.6 |
| **실행** | `relevance_service.llm_check(doc, topic)` |
| **기대결과** | is_relevant=True, score=0.87 반환 |
| **연결 요구사항** | FR-V02, FR-V03 |

### TC-V04. 2차 LLM 점수 임계값 미만 → 폐기

| 항목 | 내용 |
|------|------|
| **ID** | TC-V04 |
| **전제조건** | Mock LLM이 score=0.3 반환, threshold=0.6 |
| **실행** | `relevance_service.llm_check(doc, topic)` |
| **기대결과** | is_relevant=False 반환, 저장 안 됨 |
| **연결 요구사항** | FR-V02, FR-V03 |

### TC-V05. 문서 최소 길이 미달 → 1차 폐기

| 항목 | 내용 |
|------|------|
| **ID** | TC-V05 |
| **입력** | 본문 100자 (기준 200자) |
| **실행** | `relevance_service.rule_filter(doc, topic)` |
| **기대결과** | False 반환 |
| **연결 요구사항** | FR-V01 |

---

## 5. 모델 라우터 (Model Router)

### TC-M01. capability 기반 모델 선택

| 항목 | 내용 |
|------|------|
| **ID** | TC-M01 |
| **전제조건** | model_a: capability=["query_gen"], model_b: capability=["relevance_check"] |
| **입력** | task_type="query_gen", required_capabilities=["query_gen"] |
| **실행** | `model_router.select_model(...)` |
| **기대결과** | model_a 선택 |
| **연결 요구사항** | FR-M01, FR-M02 |

### TC-M02. 예산 초과 시 fallback 모델 선택

| 항목 | 내용 |
|------|------|
| **ID** | TC-M02 |
| **전제조건** | model_a: daily_budget=1000, used=1000 (소진). model_b: 예산 여유 있음 |
| **입력** | estimated_tokens=100 |
| **실행** | `model_router.select_model(...)` |
| **기대결과** | model_b 선택 |
| **연결 요구사항** | FR-M02, FR-M03 |

### TC-M03. 모든 모델 예산 소진 시 예외

| 항목 | 내용 |
|------|------|
| **ID** | TC-M03 |
| **전제조건** | 모든 모델 예산 소진 또는 disabled |
| **실행** | `model_router.select_model(...)` |
| **기대결과** | `NoAvailableModelError` 발생 |
| **연결 요구사항** | FR-M03 |

### TC-M04. 일일 토큰 사용량 리셋

| 항목 | 내용 |
|------|------|
| **ID** | TC-M04 |
| **전제조건** | 모델 used_tokens_today=50000, last_reset_date=어제 |
| **실행** | `usage_service.reset_daily_usage()` |
| **기대결과** | used_tokens_today=0, last_reset_date=오늘 |
| **연결 요구사항** | FR-M04 |

### TC-M05. 토큰 사용량 기록

| 항목 | 내용 |
|------|------|
| **ID** | TC-M05 |
| **전제조건** | LLM 호출 완료, input_tokens=200, output_tokens=100 |
| **실행** | `usage_service.log_usage(model_id, task_type, response)` |
| **기대결과** | model_usage_logs에 1건 삽입, model.used_tokens_today += 300 |
| **연결 요구사항** | FR-M05 |

---

## 6. 문서 저장 및 버전 관리

### TC-S01. 신규 문서 저장

| 항목 | 내용 |
|------|------|
| **ID** | TC-S01 |
| **입력** | url="https://github.com/x/y", 정제 본문, relevance_score=0.85 |
| **실행** | `document_service.upsert(doc_data)` |
| **기대결과** | documents에 1건, document_versions version_no=1에 1건 저장 |
| **연결 요구사항** | FR-S01, FR-S02, FR-S03 |

### TC-S02. 동일 URL 내용 변경 시 버전 증가

| 항목 | 내용 |
|------|------|
| **ID** | TC-S02 |
| **전제조건** | url="https://github.com/x/y" 이미 version_no=1 존재 |
| **입력** | 동일 URL, 다른 content_hash |
| **실행** | `document_service.upsert(doc_data)` |
| **기대결과** | documents.current_version=2, document_versions에 version_no=2 추가, version_no=1 보존 |
| **연결 요구사항** | FR-S03 |

### TC-S03. 동일 URL 동일 내용 재수집 → 저장 스킵

| 항목 | 내용 |
|------|------|
| **ID** | TC-S03 |
| **전제조건** | url="https://github.com/x/y" 이미 동일 content_hash로 저장됨 |
| **입력** | 동일 URL, 동일 content_hash |
| **실행** | `document_service.upsert(doc_data)` |
| **기대결과** | 새 버전 미생성, 기존 레코드 unchanged |
| **연결 요구사항** | FR-S04 |

### TC-S04. 버전 이력 조회

| 항목 | 내용 |
|------|------|
| **ID** | TC-S04 |
| **입력** | GET /documents/{doc_id}/versions |
| **실행** | API 호출 |
| **기대결과** | 200 OK, version_no 오름차순 목록 반환 |
| **연결 요구사항** | FR-S03 |

---

## 7. RAG 파이프라인

### TC-I01. 문서 청킹

| 항목 | 내용 |
|------|------|
| **ID** | TC-I01 |
| **입력** | 2000토큰 분량의 정제 본문, chunk_size=500 |
| **실행** | `rag_service.chunk_document(doc)` |
| **기대결과** | 4~5개 청크 생성, 각 청크에 token_count 기록 |
| **연결 요구사항** | FR-I01 |

### TC-I02. 임베딩 생성

| 항목 | 내용 |
|------|------|
| **ID** | TC-I02 |
| **전제조건** | Mock 임베딩 제공자, 768차원 벡터 반환 |
| **입력** | 청크 목록 |
| **실행** | `rag_service.embed_chunks(chunks)` |
| **기대결과** | 각 청크의 embedding_status="done", Qdrant에 삽입 |
| **연결 요구사항** | FR-I02 |

### TC-I03. 자연어 질의응답

| 항목 | 내용 |
|------|------|
| **ID** | TC-I03 |
| **전제조건** | 2개 문서 임베딩 완료, Mock LLM 답변 반환 |
| **입력** | POST /rag/query { "query": "로컬 LLM 에이전트 프레임워크는?", "topic_id": "t001" } |
| **실행** | API 호출 |
| **기대결과** | 200 OK, answer 텍스트 + sources 목록(url, title) 포함 |
| **연결 요구사항** | FR-A01, FR-A02 |

---

## 8. 스케줄러

### TC-SC01. 수집 파이프라인 자동 트리거

| 항목 | 내용 |
|------|------|
| **ID** | TC-SC01 |
| **전제조건** | topic.schedule_cron 도래, Mock 파이프라인 |
| **실행** | 스케줄러 tick 실행 |
| **기대결과** | 해당 주제의 파이프라인 1회 실행 기록 |
| **연결 요구사항** | FR-SC01 |

### TC-SC02. 비활성 주제 스케줄 미실행

| 항목 | 내용 |
|------|------|
| **ID** | TC-SC02 |
| **전제조건** | topic.enabled=False |
| **실행** | 스케줄러 tick 실행 |
| **기대결과** | 해당 주제 파이프라인 미실행 |
| **연결 요구사항** | FR-T01 |

---

## 9. API 입력 유효성

### TC-API01. 주제 생성 필수 필드 누락

| 항목 | 내용 |
|------|------|
| **ID** | TC-API01 |
| **입력** | POST /topics { } (빈 바디) |
| **실행** | API 호출 |
| **기대결과** | 422 Unprocessable Entity |

### TC-API02. 잘못된 cron 표현식

| 항목 | 내용 |
|------|------|
| **ID** | TC-API02 |
| **입력** | POST /topics { schedule_cron: "invalid" } |
| **실행** | API 호출 |
| **기대결과** | 422, cron 필드 오류 메시지 |

### TC-API03. 존재하지 않는 주제 조회

| 항목 | 내용 |
|------|------|
| **ID** | TC-API03 |
| **입력** | GET /topics/nonexistent_id |
| **실행** | API 호출 |
| **기대결과** | 404 Not Found |
