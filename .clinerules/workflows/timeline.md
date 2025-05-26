### 📅 프로젝트 단계별 로드맵 : 각 Phase 완료 시 회고 & 다음 단계 확정

| Phase            |  기간 | 목표                        |
| :--------------- | :-: | :------------------------ |
| **1. 기초 구축**     | 2 주 | 프로젝트 뼈대와 기본 인증 기반 마련      |
| **2. 핵심 기능**     | 3 주 | 계정·메일의 CRUD 및 OAuth 흐름 완성 |
| **3. 고급 기능**     | 3 주 | 증분 동기화·웹훅·외부 연동 확보        |
| **4. CLI & API** | 2 주 | 운영·디버깅용 CLI와 REST API 정식화 |
| **5. 최적화·배포**    | 2 주 | 퍼포먼스·보안 강화 후 자동화 배포       |

---

#### Phase 1 — 기초 구축

* **프로젝트 구조 설정**

  * `core/`, `adapters/`, `tests/`, `main.py` 폴더·모듈 초기화
  * Poetry/pyproject.toml 작성, CI 파이프라인 스켈레톤 배치
* **데이터베이스 스키마 구현**

  * `accounts`, `tokens`, `emails` 주요 테이블 DDL
  * Alembic 마이그레이션 세팅
* **기본 인증 플로우 구현**

  * Authorization Code Flow Skeleton
  * 토큰 캐싱 전략(파일/Redis) 설계 및 POC

---

#### Phase 2 — 핵심 기능

* **계정 관리 CRUD**

  * `AccountService` + REST, Typer CLI 엔드포인트 제공
* **OAuth 인증 구현**

  * 리프레시·재발급 로직, 예외 래핑(`AuthError`) 정교화
* **기본 메일 조회 기능**

  * `/me/messages` 호출 → DB 적재 → JSON 응답

---

#### Phase 3 — 고급 기능

* **Delta Query 구현**

  * `deltaLink` 저장, 증분 폴링 스케줄러
* **웹훅 처리**

  * Graph `/subscriptions` 등록, HMAC 검증, retry 전략

#### Phase 4 — 고급 기능
* **외부 API 연동**

  * 사내 “Messaging Gateway”에 변경분 POST
  * 실패 큐 + 재시도 백오프

---

#### Phase 5 — CLI

* **CLI 명령어 구현**

  * `typer` 기반 `account add/list/auth` 등 서브커맨드

#### Phase 6 — API

* **RESTful API 개발**

  * OpenAPI 문서 자동 생성 (`fastapi[all]`)
* **문서화**

  * mkdocs + material 테마, 버전 태깅

---

#### Phase 7 — 최적화 및 배포

* **성능 최적화**

  * async DB 풀, 캐싱 계층, 쿼리 프로파일링
* **보안 강화**

  * OAuth 스코프 최소화, DB 암호화 at-rest/at-transit, SAST 도입
* **배포 자동화**

  * Docker multi-stage, GitHub Actions → k8s 헬름 차트
* **통합 테스트**

  * pytest + pytest-asyncio E2E 시나리오
  * Docker-compose 서비스(메일 모킹, 웹훅 리시버) 포함

> **총 소요:** 12 주 (여유 10–15 %)—각 Phase 완료 시 회고 & 다음 단계 확정 🎯
