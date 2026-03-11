## 권장 아키텍처

전체는 7개 레이어로 나누는 게 깔끔하다.

### 1. Topic Registry

관심 주제와 수집 규칙을 관리하는 계층이다.

여기서 “키워드”는 진짜 한 단어가 아니라 **주제 정의 객체**로 가야 한다. 예를 들면:

* 주제명
    
* 목적 설명
    
* 포함해야 할 개념
    
* 제외해야 할 개념
    
* 예시 검색어
    
* 우선 도메인 regex
    
* 제외 도메인 regex
    
* 언어
    
* 수집 주기
    
* 우선순위
    
* 활성 여부
    

즉, `keyword`가 아니라 `topic_profile`에 가깝다.  
네 요구사항대로라면 검색은 이 프로필을 기반으로 생성되어야 한다.

예시 구조는 이런 느낌이다.

JSON{  
    "topic_id": "topic_001",  
    "name": "로컬 LLM 에이전트 프레임워크",  
    "description": "온프레미스 또는 로컬 환경에서 실행 가능한 에이전트 프레임워크, MCP 연동, 툴 호출, RAG 통합 사례를 추적",  
    "must_include": [  
        "local llm",  
        "agent framework",  
        "mcp",  
        "tool calling"  
    ],  
    "should_include": [  
        "ollama",  
        "vllm",  
        "rag"  
    ],  
    "must_exclude": [  
        "hosted only",  
        "openai exclusive"  
    ],  
    "preferred_domains_regex": [  
        "github\\.com",  
        "docs\\.",  
        "readthedocs\\.io"  
    ],  
    "blocked_domains_regex": [  
        ".*pinterest.*",  
        ".*spamdomain.*"  
    ],  
    "language": ["ko", "en"],  
    "priority": 8,  
    "schedule_cron": "0 */6 * * *",  
    "enabled": true  
}

이런 식으로 가야 나중에 주제별로 훨씬 정교하게 움직인다.

* * *

### 2. Query Planning

주제 설명을 기반으로 실제 검색 질의를 만드는 계층이다.

여기서 중요한 건 **질의 생성도 모델이 하되, 생성 결과를 구조화**해야 한다는 점이다. 그냥 LLM에 “검색어 만들어줘” 하면 이상한 SEO 미사여구를 뿌릴 수 있다. 아주 창의적으로 쓸모없어진다.

그래서 출력은 반드시 구조화된 형식이어야 한다.

JSON{  
    "queries": [  
        {  
            "query": "local LLM agent framework MCP tool calling ollama",  
            "intent": "broad",  
            "language": "en"  
        },  
        {  
            "query": "온프레미스 LLM 에이전트 MCP 도구 호출 RAG",  
            "intent": "broad",  
            "language": "ko"  
        },  
        {  
            "query": "site:github.com MCP local agent ollama",  
            "intent": "preferred_domain",  
            "language": "en"  
        }  
    ]  
}

여기서 포인트는:

* 일반 검색어
    
* 사이트 편향 검색어
    
* 한국어/영어 검색어
    
* 넓은 검색 / 좁은 검색
    

이렇게 **복수 후보 질의**를 만들고, 주제당 n개 정도만 유지하는 구조가 좋다.

* * *

### 3. Retrieval Orchestrator

실제 검색을 수행하는 계층이다.

여기서는 Brave 같은 검색 API, RSS, 특정 사이트 직접 크롤링, 향후 다른 API를 한 인터페이스로 감싼다.

예를 들면:

* `SearchProvider.search(query, options)`
    
* `Fetcher.fetch(url)`
    
* `Extractor.extract(html)`
    

이렇게 provider 인터페이스로 분리해야 한다.  
안 그러면 나중에 검색 API 하나 바꿀 때 프로젝트 전체가 같이 운다.

추천 흐름은 이렇다.

Plain text주제 선택  
→ 질의 후보 생성  
→ preferred domain 우선 반영  
→ 검색 API 호출  
→ blocked/preferred regex 필터  
→ URL 중복 제거  
→ 본문 추출  
→ relevance 검사  
→ 저장

* * *

### 4. Relevance Validator

이게 네 요구사항에서 꽤 핵심이다.  
**검색 결과가 원래 목표와 맞는지 체크**하는 계층.

이걸 안 넣으면 금방 주제 오염된다. 예를 들어 “agent” 검색했더니 부동산 중개인(agent), 보험 agent, 게임 캐릭터 agent가 섞이는 대참사가 난다. 단어는 innocent한데 세상은 늘 구정물이다.

검증은 2단계가 좋다.

#### 1차: 규칙 기반 필터

* 제목/본문에 필수 키워드 포함 여부
    
* 제외 키워드 존재 여부
    
* preferred / blocked domain 적용
    
* 언어 감지
    
* 너무 짧은 문서 제외
    

#### 2차: LLM 또는 임베딩 기반 의미 검증

* “이 문서는 topic description과 얼마나 부합하는가?”
    
* score 0~1
    
* reason 요약
    
* 저장 여부 결정
    

예시 출력:

JSON{  
    "is_relevant": true,  
    "score": 0.87,  
    "reason": "문서가 로컬 LLM 기반 에이전트 프레임워크와 MCP 연동 사례를 직접 다룸"  
}

이 relevance validator는 **가벼운 모델**로 먼저 돌리고, 애매한 경우만 더 비싼 모델로 넘기는 계단형 구조가 좋다.

* * *

## 모델 후보 풀과 토큰 예산 관리

이 부분이 아주 중요하다. 네 요구사항의 엔진룸이다.

### 기본 원칙

모델은 작업 유형별로 후보군을 갖고, 각 후보는 다음 속성을 가진다.

* provider: local / api
    
* model_name
    
* capability_tags: query_gen, relevance_check, summarize, answer, rerank
    
* max_context
    
* cost_input_per_1k
    
* cost_output_per_1k
    
* daily_budget_tokens
    
* used_tokens_today
    
* priority
    
* fallback_order
    
* enabled
    

즉, 모델을 하나의 “실행 리소스”로 다루는 거다.

예시:

JSON{  
    "model_id": "model_api_01",  
    "provider": "openai",  
    "model_name": "gpt-x-mini",  
    "capability_tags": ["query_gen", "relevance_check", "summarize"],  
    "daily_budget_tokens": 300000,  
    "used_tokens_today": 125000,  
    "priority": 1,  
    "enabled": true  
}

로컬 모델도 동일한 포맷으로 넣는다.

JSON{  
    "model_id": "model_local_01",  
    "provider": "ollama",  
    "model_name": "qwen3:8b",  
    "capability_tags": ["relevance_check", "summarize", "answer"],  
    "daily_budget_tokens": 999999999,  
    "used_tokens_today": 0,  
    "priority": 2,  
    "enabled": true  
}

### 모델 선택 방식

한 파이프라인 안에서도 모델을 적극적으로 바꾸려면 **Task Router**가 필요하다.

예를 들면:

* 질의 생성 → 작은 API 모델
    
* relevance check 1차 → 로컬 소형 모델
    
* relevance check 2차 → API 중형 모델
    
* 요약 → 로컬 또는 저가 API 모델
    
* 최종 답변 → 사용자가 선택한 모델
    

즉, 파이프라인이 모델에 종속되면 안 되고, **작업(task)이 요구 capability만 선언**해야 한다.

예:

Python실행됨task = {  
    "type": "relevance_check",  
    "required_capabilities": ["relevance_check"],  
    "max_cost": 0.02,  
    "latency_preference": "fast",  
    "quality_preference": "medium"  
}

라우터는 여기서 모델 후보를 골라서 실행한다.

### 토큰 소진 시 다음 후보 실행

이건 아주 자연스럽게 **Candidate Chain**으로 처리한다.

Plain text[primary model]  
→ 예산 초과 / rate limit / 오류  
→ [secondary model]  
→ 또 실패  
→ [tertiary model]

토큰 예산은 일단위로 리셋하면 된다.  
리셋은 날짜 기준으로 `Asia/Seoul` 맞춰서 처리하는 게 좋다.

예산 판단 예시:

Python실행됨def can_run(model, estimated_input_tokens, estimated_output_tokens):  
    estimated_total = estimated_input_tokens + estimated_output_tokens  
    return (model.used_tokens_today + estimated_total) <= model.daily_budget_tokens

그리고 실제 토큰 사용량은 가능하면 provider 응답 기준으로 기록하고, 없으면 추정치로 보정한다.

* * *

## 스케줄링 구조

수집 interval도 주제별, 작업별로 나뉘어야 한다.

* Topic Scan: 검색 결과 신규 수집
    
* Revalidation: 기존 문서 relevance 재평가
    
* Re-embedding: 임베딩 모델 변경 시 재색인
    
* Archive Rotation: 오래된 문서 아카이빙
    
* Usage Reset: 일일 토큰 사용량 초기화
    

스케줄러는 초반엔 단순하게 가도 된다.

* Python + APScheduler
    
* 또는 시스템 cron / Windows 작업 스케줄러
    
* 작업 큐가 필요해지면 Celery / RQ / Dramatiq
    

개인용이면 처음부터 메시지 브로커까지 갈 필요는 없다.  
작게 시작해야 한다. 대포로 모기 잡겠다고 집까지 날려버리면 안 된다.

* * *

## 저장소 설계

여기서 가장 중요하게 분리할 건 5종류다.

### 1. Topic metadata

주제 정의와 규칙

### 2. Search run history

언제 어떤 질의로 어떤 결과가 나왔는지

### 3. Raw document archive

원문 HTML, 원본 응답, fetch 결과

### 4. Normalized document store

정제된 본문, 메타데이터, relevance score

### 5. RAG index artifacts

청크, 임베딩, 벡터 인덱스, 키워드 인덱스

이걸 분리 안 하면 나중에 “문서 삭제했더니 히스토리까지 날아갔네”, “본문 업데이트했더니 과거 증거가 사라졌네” 같은 이상한 일 생긴다.

* * *

## 아카이빙과 과거 이력 조회

네가 말한 “수집한 데이터, rag 저장문서들의 아카이빙처리, 과거이력 조회”는 반드시 **immutable log + active view** 구조로 가야 한다.

즉:

* 현재 활성 문서 테이블
    
* 과거 버전/과거 상태 로그 테이블
    

이중 구조다.

예를 들어 같은 URL이 3번 업데이트되면:

* `documents`에는 최신 활성 버전만 유지
    
* `document_versions`에는 1, 2, 3 버전 전부 저장
    

그래야 “이 문서 예전에 뭐라고 했더라?”가 가능하다.  
세상은 자주 말을 바꾸고, 인터넷은 그 흔적을 지운 척한다. 우리는 그걸 몰래 보관하면 된다. 아주 건전한 집착이다.

### 추천 DB 테이블 개요

#### topics

Plain texttopic_id  
name  
description  
priority  
enabled  
schedule_cron  
created_at  
updated_at

#### topic_rules

Plain textrule_id  
topic_id  
rule_type          # preferred_domain / blocked_domain / include / exclude  
pattern  
is_regex  
enabled  
created_at  
updated_at

#### search_queries

Plain textquery_id  
topic_id  
query_text  
query_language  
intent  
generated_by_model  
created_at  
expires_at

#### search_runs

Plain textrun_id  
topic_id  
query_id  
provider  
started_at  
finished_at  
status  
result_count  
error_message

#### raw_documents

Plain textraw_doc_id  
url  
fetched_at  
http_status  
content_hash  
raw_html_path  
raw_json_path

#### documents

Plain textdoc_id  
topic_id  
url  
title  
author  
published_at  
collected_at  
language  
normalized_text  
summary  
relevance_score  
relevance_reason  
current_version  
is_active

#### document_versions

Plain textversion_id  
doc_id  
version_no  
content_hash  
normalized_text  
summary  
relevance_score  
created_at  
change_type

#### chunks

Plain textchunk_id  
doc_id  
version_no  
chunk_index  
chunk_text  
token_count  
embedding_model  
embedding_status

#### model_registry

Plain textmodel_id  
provider  
model_name  
capability_tags  
daily_budget_tokens  
used_tokens_today  
priority  
enabled  
last_reset_date

#### model_usage_logs

Plain textusage_id  
model_id  
task_type  
input_tokens  
output_tokens  
cost_estimate  
executed_at  
status

이 정도면 꽤 튼튼하다.

* * *

## 사이트 우선/회피 리스트 관리

이건 **정규표현식 기반 룰 엔진**으로 분리하는 게 정석이다.

룰 타입:

* preferred_domain_regex
    
* blocked_domain_regex
    
* preferred_url_regex
    
* blocked_url_regex
    

적용 순서도 중요하다.

Plain text1. blocked_url_regex  
2. blocked_domain_regex  
3. preferred_url_regex  
4. preferred_domain_regex

즉, 차단이 우선이다.  
괜히 “우선 사이트인데 차단에도 걸리네?” 같은 철학 토론하지 말고, 차단 우선으로 명확히 가는 게 낫다.

관리 기능은 최소한 이게 있어야 한다.

* 룰 추가
    
* 룰 수정
    
* 룰 비활성화
    
* 룰 삭제
    
* 테스트 매칭
    
* 우선순위 조정
    

“테스트 매칭”이 은근 중요하다. regex는 늘 자신감이 넘치고, 그 자신감은 자주 틀린다.

예시:

Python실행됨def classify_url(url, rules):  
    for rule in rules.blocked_url:  
        if re.search(rule.pattern, url):  
            return "blocked"  
    for rule in rules.blocked_domain:  
        if re.search(rule.pattern, get_domain(url)):  
            return "blocked"  
    for rule in rules.preferred_url:  
        if re.search(rule.pattern, url):  
            return "preferred"  
    for rule in rules.preferred_domain:  
        if re.search(rule.pattern, get_domain(url)):  
            return "preferred"  
    return "neutral"

* * *

## RAG 저장문서와 아카이브 분리

이 부분도 중요하다.  
RAG에 들어가는 건 “검색용 가공본”이고, 아카이브는 “증거 보관소”다.

즉, 하나의 문서에 대해:

* 원문 HTML
    
* 정제 텍스트
    
* 요약
    
* 청크
    
* 임베딩
    
* 최종 인용용 메타데이터
    

가 따로 있어야 한다.

그리고 오래된 문서는 세 단계로 관리할 수 있다.

### Active

최근 문서, 검색 우선 대상

### Warm Archive

과거 문서, 필요 시 검색 가능

### Cold Archive

원문 보관만 유지, 기본 검색 제외

예를 들어 90일 이상 지나고 relevance 낮은 건 warm으로, 1년 지나면 cold로 내리는 식이다.

* * *

## 추천 파이프라인

전체 실행 파이프라인은 이 정도가 좋다.

Plain text[1] topic load  
[2] query generate  
[3] search retrieve  
[4] url/domain rule filter  
[5] raw fetch  
[6] content extract  
[7] rule-based relevance filter  
[8] llm relevance check  
[9] normalize & summarize  
[10] archive raw/original  
[11] upsert document + versioning  
[12] chunking  
[13] embedding  
[14] rag index update  
[15] run log / model usage log update

여기서 8~9~13 단계는 서로 다른 모델을 써도 된다.  
이게 네가 원하는 “한 파이프라인 안에서도 적극적인 모델 변경”에 정확히 맞는다.

* * *

## 구현 기술 추천

너 목적이 “가볍게”니까 초반 스택은 이렇게 추천한다.

### 백엔드

* Python
    
* FastAPI
    
* SQLAlchemy
    
* Pydantic
    

### DB

* SQLite로 시작
    
* 나중에 PostgreSQL로 이동 가능하게 ORM 사용
    

### 문서 저장

* 로컬 파일 시스템
    
* `data/raw/YYYY/MM/DD/...`
    
* `data/normalized/...`
    
* `data/archive/...`
    

### 검색/임베딩

* SQLite FTS5 + Qdrant
    
* 또는 처음엔 Chroma도 가능
    
* 임베딩 모델은 multilingual 계열
    

### 스케줄

* APScheduler
    

### LLM 추상화

* provider adapter 패턴
    
    * OllamaAdapter
        
    * OpenAICompatibleAdapter
        
    * AnthropicAdapter
        
    * GeminiAdapter 같은 식
        

### 본문 추출

* trafilatura 기본
    
* 실패 시 readability-lxml
    
* 그래도 실패하면 playwright fallback
    

* * *

## 설계 원칙 5개

### 1. 주제와 질의를 분리

주제는 사람이 정의하고, 질의는 시스템이 생성한다.

### 2. 원문과 RAG 가공본을 분리

증거 보관과 검색 최적화는 목적이 다르다.

### 3. 모델과 작업을 분리

파이프라인은 모델 이름을 몰라야 한다.

### 4. 현재 상태와 이력을 분리

최신 문서 조회와 과거 버전 조회를 동시에 만족시킨다.

### 5. 규칙 기반 필터와 LLM 판단을 같이 쓴다

LLM만 믿으면 느리고 비싸고 헛소리도 한다. 규칙만 쓰면 둔하다. 둘을 섞어야 한다.

* * *

## MVP 범위

처음부터 너무 야심차게 가면 귀신 나온다.  
MVP는 이 정도면 충분하다.

### 1차 MVP

* topic 등록/수정/삭제
    
* regex rule 등록/수정/삭제
    
* 주제 설명 기반 검색어 생성
    
* 검색 결과 수집
    
* relevance check
    
* raw/normalized 저장
    
* chunk + embedding
    
* 문서 검색 + 답변
    
* 모델 후보 풀 + 일일 토큰 제한 + fallback
    

### 2차

* 과거 버전 비교
    
* 주제별 수집 성공률/오탐률 대시보드
    
* archive tier 전환
    
* 모델별 비용 리포트
    

### 3차

* 주제별 자동 브리핑
    
* 새 문서 요약 digest
    
* 중요도 변화 감지
    
* 오래된 검색어 자동 재생성
    

* * *

## 추천 디렉터리 구조

Plain textproject/  
├─ app/  
│  ├─ api/  
│  ├─ core/  
│  ├─ db/  
│  ├─ models/  
│  ├─ services/  
│  │  ├─ topic_service.py  
│  │  ├─ query_planner.py  
│  │  ├─ search_service.py  
│  │  ├─ fetch_service.py  
│  │  ├─ relevance_service.py  
│  │  ├─ archive_service.py  
│  │  ├─ rag_service.py  
│  │  ├─ model_router.py  
│  │  └─ usage_service.py  
│  ├─ providers/  
│  │  ├─ llm/  
│  │  ├─ search/  
│  │  └─ extractor/  
│  └─ scheduler/  
├─ data/  
│  ├─ raw/  
│  ├─ normalized/  
│  ├─ archive/  
│  └─ index/  
├─ tests/  
├─ scripts/  
└─ config/

이렇게 가면 나중에 안 울 확률이 올라간다.

* * *

## 결론

네 요구사항을 만족하는 정답 구조는 **“주제 중심 + 작업 중심 + 모델 라우팅 중심”**이다.

즉,

* 키워드는 단어가 아니라 **설명 포함 주제 프로필**
    
* 수집 결과는 **주제 적합성 검증**을 거쳐 저장
    
* 문서는 **원문 / 정제본 / RAG 인덱스 / 이력**으로 분리
    
* 사이트 제어는 **regex 룰 엔진**으로 관리
    
* 모델은 **후보 풀 + 일일 토큰 예산 + fallback chain**으로 운영
    
* 한 파이프라인 안에서도 **작업별 모델 교체**가 가능해야 한다
    

이 구조면 가볍게 시작하면서도 나중에 꽤 오래 버틴다. 억지로 거대한 플랫폼 만들 필요 없다. 작고 단단한 관측소부터 만드는 게 맞다.

다음 단계로 바로 이어서 해줄 수 있는 건 두 가지 중 하나다.  
**“DB 스키마 SQL 초안”**으로 바로 내려가거나, **“FastAPI + Python 기준 MVP 폴더/클래스 설계”**로 내려갈 수 있다.