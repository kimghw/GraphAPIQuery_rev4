# Microsoft 365 Graph API Mail Processing System

클린 아키텍처 기반의 Microsoft 365 Graph API를 활용한 메일 처리 시스템입니다.

## 🚀 프로젝트 현황

### ✅ 1단계: 기초구축 완료 (2025.01.26)

**완료된 작업:**
- ✅ 클린 아키텍처 기반 프로젝트 구조 설계
- ✅ 도메인 엔티티 정의 (Account, Token, Mail, SyncHistory 등)
- ✅ 포트/어댑터 패턴 적용한 인터페이스 설계
- ✅ 핵심 유즈케이스 구현
  - AccountManagementUseCase: 계정 등록/관리
  - AuthenticationUseCase: OAuth 2.0 인증 (Authorization Code Flow, Device Code Flow)
  - MailProcessingUseCase: 메일 조회/발송/동기화
- ✅ 설정 관리 시스템 설계
- ✅ 아키텍처 문서 작성

### ✅ 2단계: 인증 시스템 완료 (2025.01.26)

**완료된 작업:**
- ✅ OAuth 2.0 Authorization Code Flow 구현
- ✅ OAuth 2.0 Device Code Flow 구현
- ✅ 토큰 관리 시스템 (자동 갱신, 암호화 저장)
- ✅ Graph API 클라이언트 어댑터
- ✅ 암호화 서비스 (AES-256)
- ✅ 캐시 서비스 (Redis/메모리)
- ✅ CLI 인증 명령어 구현
- ✅ 어댑터 팩토리 패턴 구현

**다음 단계:**
- 🔄 3단계: 메일 처리 시스템 구현
- 🔄 4단계: API 서버 및 웹 인터페이스
- 🔄 5단계: 테스트 및 배포 준비

## 프로젝트 구조

```
GraphAPIQuery_rev4/
├── core/                    # 🎯 핵심 비즈니스 로직 (완료)
│   ├── domain/             # 도메인 엔티티 및 포트 인터페이스
│   │   ├── __init__.py
│   │   ├── entities.py     # Account, Token, Mail 등 엔티티
│   │   └── ports.py        # Repository, Service 포트 정의
│   └── usecases/           # 애플리케이션 유즈케이스
│       ├── __init__.py
│       ├── account_management.py    # 계정 관리
│       ├── authentication.py       # OAuth 인증
│       └── mail_processing.py      # 메일 처리
├── adapters/               # 🔧 외부 어댑터 (예정)
│   ├── api/                # FastAPI 라우터
│   ├── cli/                # CLI 인터페이스
│   ├── db/                 # 데이터베이스 어댑터
│   └── external/           # 외부 API 어댑터
├── config/                 # ⚙️ 설정 관리 (설계 완료)
├── docs/                   # 📚 문서
│   └── ARCHITECTURE.md     # 아키텍처 문서
├── tests/                  # 🧪 테스트 (예정)
├── pyproject.toml          # 프로젝트 설정
├── .env.example            # 환경변수 예제
└── README.md               # 프로젝트 문서
```

## 주요 기능

### 인증 및 계정 관리
- ✅ 다중 Microsoft 365 계정 등록 및 관리
- ✅ OAuth 2.0 Authorization Code Flow 지원
- ✅ Device Code Flow 지원
- ✅ 자동 토큰 갱신 메커니즘
- ✅ 권한 범위(Scope) 관리 및 재동의 처리
- ✅ 토큰 암호화 저장

### 메일 처리
- ✅ 메일 조회 (기간별, 필터별, 송수신별)
- ✅ 메일 발송 기능
- ✅ 증분 동기화 (Delta Query)
- ✅ 메일 데이터 외부 API 전송
- ✅ 동기화 이력 관리
- 🔄 첨부파일 처리 및 스토리지 연동 (예정)
- 🔄 실시간 푸시 알림 (Webhook) (예정)

## 아키텍처 설계

### 클린 아키텍처 원칙
- **Core Layer**: 비즈니스 로직과 도메인 규칙이 외부 의존성 없이 독립적으로 구현
- **Adapters Layer**: 외부 시스템(DB, API, UI)과의 연결을 담당하는 얇은 어댑터 레이어
- **Ports**: Core와 Adapters 간의 인터페이스 정의

### 의존성 방향
```
Adapters → Core (Ports/Interfaces)
```

### 핵심 엔티티
- **Account**: Microsoft 365 계정 정보 및 상태 관리
- **Token**: OAuth 토큰 정보 및 만료 관리
- **Mail**: 메일 메시지 정보 및 처리 상태
- **SyncHistory**: 동기화 이력 및 결과 추적
- **DeltaLink**: 증분 동기화를 위한 델타 링크 관리

### 주요 유즈케이스

#### 1. AccountManagementUseCase
```python
# 계정 등록
account = await account_usecase.register_account(
    email="user@example.com",
    auth_type=AuthType.AUTHORIZATION_CODE,
    client_id="your_client_id",
    client_secret="your_client_secret",
    redirect_uri="http://localhost:8080/callback",
    tenant_id="your_tenant_id"
)

# 계정 조회
accounts = await account_usecase.list_active_accounts()
```

#### 2. AuthenticationUseCase
```python
# Authorization Code Flow 시작
auth_url, state = await auth_usecase.start_authorization_code_flow(
    account_id=account.id,
    scope="https://graph.microsoft.com/.default"
)

# 인증 완료
token = await auth_usecase.complete_authorization_code_flow(
    code="auth_code",
    state=state
)

# Device Code Flow
device_info = await auth_usecase.start_device_code_flow(account_id)
token = await auth_usecase.poll_device_code_flow(device_info['device_code'])
```

#### 3. MailProcessingUseCase
```python
# 메일 조회 (데이터베이스에서 토큰 자동 조회)
mails = await mail_usecase.list_mails(
    account_id=account.id,
    top=50,
    start_date=datetime.now() - timedelta(days=7)
)

# 메일 동기화
sync_history = await mail_usecase.sync_mails(
    account_id=account.id,
    use_delta=True,
    batch_size=100
)

# 메일 발송
success = await mail_usecase.send_mail(
    account_id=account.id,
    to_recipients=["recipient@example.com"],
    subject="Test Email",
    body_content="<h1>Hello World</h1>",
    body_content_type="HTML"
)
```

## 설정 관리

### 환경별 설정 지원
- **Development**: 개발 환경 설정
- **Production**: 운영 환경 설정  
- **Testing**: 테스트 환경 설정

### 필수 환경 변수
```bash
# 환경 설정
ENVIRONMENT=development  # development, production, testing

# 데이터베이스
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

# Redis
REDIS_URL=redis://localhost:6379

# Microsoft Graph API
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_TENANT_ID=your_tenant_id

# OAuth 설정
OAUTH_REDIRECT_URI=http://localhost:8080/auth/callback
OAUTH_STATE_SECRET=your_oauth_state_secret

# 암호화
ENCRYPTION_KEY=your_32_byte_encryption_key

# JWT
JWT_SECRET_KEY=your_jwt_secret_key

# 웹훅
WEBHOOK_SECRET=your_webhook_secret

# 로깅
LOG_LEVEL=INFO
```

## 보안 설계

### 토큰 보안
- **AES-256 암호화**: 모든 토큰은 암호화되어 데이터베이스에 저장
- **자동 갱신**: 만료 임박 토큰 자동 갱신 메커니즘
- **안전한 폐기**: 토큰 폐기 시 완전 삭제

### 인증 보안
- **State 검증**: CSRF 공격 방지를 위한 State 파라미터 검증
- **HTTPS 필수**: 모든 OAuth 통신은 HTTPS로 진행
- **권한 범위 관리**: 최소 권한 원칙 적용

## 개발 진행 상황

### ✅ 완료된 작업
1. **프로젝트 구조 설계**: 클린 아키텍처 기반 폴더 구조
2. **도메인 모델링**: 핵심 엔티티 및 비즈니스 규칙 정의
3. **포트 인터페이스**: 외부 의존성과의 계약 정의
4. **유즈케이스 구현**: 핵심 비즈니스 로직 구현
5. **설정 시스템**: 환경별 설정 관리 시스템 설계
6. **문서화**: 아키텍처 및 설계 문서 작성

### 🔄 다음 단계 (2단계: 어댑터 구현)
1. **데이터베이스 어댑터**: PostgreSQL 연동 및 Repository 구현
2. **Graph API 클라이언트**: Microsoft Graph API 연동
3. **암호화 서비스**: 토큰 암호화/복호화 구현
4. **캐시 서비스**: Redis 연동
5. **로깅 시스템**: 구조화된 로깅 구현

### 🔄 3단계: 인터페이스 구현
1. **FastAPI 라우터**: REST API 엔드포인트
2. **CLI 인터페이스**: Typer 기반 명령행 도구
3. **의존성 주입**: 컨테이너 및 팩토리 구현

### 🔄 4단계: 테스트 및 배포
1. **단위 테스트**: 유즈케이스 및 도메인 로직 테스트
2. **통합 테스트**: 어댑터 및 외부 연동 테스트
3. **Docker 컨테이너**: 배포용 컨테이너 이미지
4. **CI/CD 파이프라인**: 자동화된 빌드 및 배포

## 기술 스택

- **언어**: Python 3.11+
- **웹 프레임워크**: FastAPI
- **CLI**: Typer
- **데이터베이스**: PostgreSQL
- **캐시**: Redis
- **ORM**: SQLAlchemy (비동기)
- **검증**: Pydantic
- **테스트**: pytest
- **컨테이너**: Docker

## 라이선스

MIT License

---

## 개발 참고사항

### 클린 아키텍처 가이드라인
- Core 레이어는 외부 의존성을 가지지 않음
- 모든 외부 연동은 포트/어댑터 패턴으로 구현
- 비즈니스 로직은 유즈케이스에서 구현
- 엔티티는 순수한 도메인 객체로 유지

### 코딩 컨벤션
- 모든 함수와 클래스에 타입 힌트 적용
- Pydantic 모델을 통한 데이터 검증
- 비동기 프로그래밍 패턴 적용
- 구조화된 로깅 및 예외 처리

### 보안 고려사항
- 모든 민감 정보는 암호화 저장
- 환경변수를 통한 설정 관리
- 최소 권한 원칙 적용
- 감사 로깅 구현
