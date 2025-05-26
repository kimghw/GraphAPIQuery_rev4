# 기술 컨텍스트 및 설정

## 초기 기술 스택

### 핵심 기술
- **Python**: 3.11+
- **프레임워크**: FastAPI (웹), Typer (CLI)
- **ORM**: SQLAlchemy 2.0 (비동기)
- **데이터베이스**: SQLite (개발), PostgreSQL (운영 예정)
- **데이터 검증**: Pydantic V2
- **CLI UI**: Rich (테이블, 프로그레스바)
- **로깅**: Python logging + structlog (예정)

### 개발 도구
- **의존성 관리**: Poetry (pyproject.toml)
- **테스트**: pytest
- **타입 체크**: mypy (예정)
- **코드 포맷**: black, isort (예정)

### 외부 API
- **Microsoft Graph API**: OAuth 2.0 인증
- **Azure AD**: 테넌트 및 앱 등록

## 현재 설정 상태

### 환경 설정 (.env)
```bash
# 데이터베이스
DATABASE_URL=sqlite:///./dev_database.db

# Microsoft Graph API (예정)
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_TENANT_ID=your_tenant_id
AZURE_REDIRECT_URI=http://localhost:8000/auth/callback

# 환경
ENVIRONMENT=development
```

### 의존성 (pyproject.toml)
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
uvicorn = "^0.24.0"
sqlalchemy = "^2.0.23"
alembic = "^1.12.1"
pydantic = "^2.5.0"
typer = "^0.9.0"
rich = "^13.7.0"
aiosqlite = "^0.19.0"
python-dotenv = "^1.0.0"
```

## 변경 사항 이력

### ✅ 완료된 설정
- [x] 프로젝트 구조 설정 (클린 아키텍처)
- [x] SQLAlchemy 2.0 비동기 설정
- [x] Pydantic V2 모델 정의
- [x] Typer CLI 인터페이스
- [x] Rich 테이블 출력
- [x] 환경 기반 설정 관리
- [x] 포트/어댑터 패턴 구현

### 🔄 진행 중인 변경사항
- [ ] OAuth 2.0 라이브러리 추가 (2단계)
- [ ] 토큰 암호화 라이브러리 (cryptography)
- [ ] HTTP 클라이언트 (httpx 또는 aiohttp)
- [ ] 로깅 구조화 (structlog)

### 📋 예정된 변경사항
- [ ] FastAPI 라우터 구현 (4단계)
- [ ] PostgreSQL 어댑터 (운영 환경)
- [ ] Redis 캐시 (성능 최적화)
- [ ] 모니터링 도구 (Prometheus, Grafana)

## 외부 API 설정

### Microsoft Graph API
- **베이스 URL**: `https://graph.microsoft.com/v1.0`
- **인증**: OAuth 2.0 Authorization Code Flow, Device Code Flow
- **스코프**: 
  - `https://graph.microsoft.com/Mail.Read`
  - `https://graph.microsoft.com/Mail.Send`
  - `https://graph.microsoft.com/User.Read`

### Azure AD 앱 등록 요구사항
- **앱 타입**: 웹 애플리케이션
- **리디렉션 URI**: `http://localhost:8000/auth/callback`
- **API 권한**: Microsoft Graph 위임된 권한
- **인증서/비밀**: 클라이언트 비밀 생성 필요

## 보안 고려사항

### 토큰 보안
- **저장**: 암호화된 형태로 데이터베이스 저장
- **전송**: HTTPS 필수
- **만료**: 자동 갱신 메커니즘
- **무효화**: 로그아웃 시 즉시 삭제

### 설정 보안
- **환경변수**: 민감한 정보는 .env 파일
- **프로덕션**: 환경변수 또는 시크릿 관리 서비스
- **검증**: Pydantic validator로 필수값 체크

## 성능 최적화

### 비동기 처리
- **데이터베이스**: SQLAlchemy 비동기 세션
- **HTTP 요청**: aiohttp 또는 httpx
- **동시성**: asyncio 기반 처리

### 캐싱 전략 (예정)
- **토큰 캐시**: 메모리 또는 Redis
- **API 응답 캐시**: 단기 캐싱
- **설정 캐시**: 애플리케이션 시작 시 로드

## 테스트 전략

### 단위 테스트
- **도메인 로직**: 순수 함수 테스트
- **유즈케이스**: Mock Repository 사용
- **어댑터**: 실제 구현 테스트

### 통합 테스트
- **데이터베이스**: 테스트 DB 사용
- **API**: TestClient 사용
- **CLI**: subprocess 또는 직접 호출

### E2E 테스트 (예정)
- **인증 플로우**: 실제 Azure AD 연동
- **Graph API**: 실제 API 호출
- **전체 워크플로우**: 계정 등록부터 메일 처리까지

## 배포 전략 (예정)

### 개발 환경
- **로컬**: SQLite + 개발 서버
- **Docker**: 컨테이너화된 환경
- **CI/CD**: GitHub Actions

### 운영 환경
- **데이터베이스**: PostgreSQL
- **웹 서버**: Uvicorn + Nginx
- **모니터링**: 로그 수집 및 메트릭
- **백업**: 정기적인 데이터 백업
