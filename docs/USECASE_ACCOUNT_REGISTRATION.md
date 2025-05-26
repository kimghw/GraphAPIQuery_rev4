# 계정 등록 유즈케이스 가이드

Microsoft Graph API Query 프로젝트의 계정 등록 유즈케이스 사용법을 설명합니다.

## 개요

`AccountManagementUseCase.register_account()` 메서드는 새로운 Microsoft 365 계정을 시스템에 등록하는 핵심 비즈니스 로직입니다.

## 메서드 시그니처

```python
async def register_account(
    self,
    email: str,
    auth_type: AuthType,
    display_name: Optional[str] = None,
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> Account:
```

## 매개변수

### 필수 매개변수
- **email** (str): Microsoft 365 계정 이메일 주소
- **auth_type** (AuthType): 인증 방식
  - `AuthType.AUTHORIZATION_CODE`: Authorization Code Flow
  - `AuthType.DEVICE_CODE`: Device Code Flow

### 선택적 매개변수
- **display_name** (Optional[str]): 계정 표시 이름
- **tenant_id** (Optional[str]): Azure AD 테넌트 ID
- **client_id** (Optional[str]): Azure 애플리케이션 클라이언트 ID
- **client_secret** (Optional[str]): 클라이언트 시크릿 (Authorization Code Flow만 필요)
- **redirect_uri** (Optional[str]): 리다이렉트 URI (Authorization Code Flow만 필요)

## 인증 방식별 필수 정보

### Authorization Code Flow
다음 정보가 모두 필요합니다:
- `client_id`
- `client_secret`
- `redirect_uri`
- `tenant_id`

### Device Code Flow
다음 정보가 필요합니다:
- `client_id`
- `tenant_id`

## 사용 예제

### 1. Authorization Code Flow 계정 등록

```python
import asyncio
from core.usecases.account_management import AccountManagementUseCase
from core.domain.entities import AuthType

async def register_auth_code_account():
    # 유즈케이스 인스턴스 생성 (의존성 주입)
    usecase = AccountManagementUseCase(
        account_repository=account_repo,
        auth_config_repository=auth_config_repo,
        logger=logger,
    )
    
    try:
        account = await usecase.register_account(
            email="user@company.com",
            auth_type=AuthType.AUTHORIZATION_CODE,
            display_name="Company User",
            tenant_id="your-tenant-id",
            client_id="your-client-id",
            client_secret="your-client-secret",
            redirect_uri="http://localhost:8080/auth/callback"
        )
        
        print(f"계정 등록 성공: {account.id}")
        print(f"이메일: {account.email}")
        print(f"상태: {account.status}")
        
    except ValueError as e:
        print(f"등록 실패: {e}")
```

### 2. Device Code Flow 계정 등록

```python
async def register_device_code_account():
    usecase = AccountManagementUseCase(
        account_repository=account_repo,
        auth_config_repository=auth_config_repo,
        logger=logger,
    )
    
    try:
        account = await usecase.register_account(
            email="user@company.com",
            auth_type=AuthType.DEVICE_CODE,
            display_name="Company User",
            tenant_id="your-tenant-id",
            client_id="your-client-id"
        )
        
        print(f"계정 등록 성공: {account.id}")
        
    except ValueError as e:
        print(f"등록 실패: {e}")
```

### 3. CLI를 통한 계정 등록

현재 구현된 CLI 명령어:

```bash
# Authorization Code Flow
python main.py account register user@company.com \
    --auth-type authorization_code \
    --display-name "Company User"

# Device Code Flow  
python main.py account register user@company.com \
    --auth-type device_code \
    --display-name "Company User"
```

## 비즈니스 로직 흐름

### 1. 입력 검증
```python
# 중복 계정 확인
if await self.account_repository.exists_by_email(email):
    raise ValueError(f"이미 등록된 계정입니다: {email}")

# 인증 방식별 필수 정보 검증
if auth_type == AuthType.AUTHORIZATION_CODE:
    if not all([client_id, client_secret, redirect_uri, tenant_id]):
        raise ValueError("Authorization Code Flow에는 필수 정보가 누락되었습니다")
```

### 2. 계정 엔티티 생성
```python
account = Account(
    email=email,
    display_name=display_name,
    auth_type=auth_type,
    tenant_id=tenant_id,
)
```

### 3. 데이터베이스 저장
```python
# 계정 저장
created_account = await self.account_repository.create(account)

# 인증 설정 저장
if auth_type == AuthType.AUTHORIZATION_CODE:
    auth_config = AuthCodeConfig(...)
    await self.auth_config_repository.create_auth_code_config(auth_config)
elif auth_type == AuthType.DEVICE_CODE:
    auth_config = DeviceCodeConfig(...)
    await self.auth_config_repository.create_device_code_config(auth_config)
```

### 4. 로깅 및 반환
```python
self.logger.info(f"계정 등록 완료: {created_account.id}, {email}")
return created_account
```

## 반환값

성공 시 생성된 `Account` 엔티티를 반환합니다:

```python
Account(
    id=UUID('...'),
    email='user@company.com',
    display_name='Company User',
    auth_type=AuthType.AUTHORIZATION_CODE,
    status=AccountStatus.INACTIVE,  # 초기 상태는 비활성
    tenant_id='your-tenant-id',
    created_at=datetime(...),
    updated_at=datetime(...),
    last_sync_at=None
)
```

## 예외 처리

### ValueError 예외 발생 상황
1. **중복 계정**: 이미 등록된 이메일 주소
2. **필수 정보 누락**: 인증 방식에 필요한 정보가 없는 경우
3. **잘못된 이메일 형식**: 엔티티 검증에서 실패

### 예외 처리 예제
```python
try:
    account = await usecase.register_account(...)
except ValueError as e:
    if "이미 등록된 계정" in str(e):
        print("중복 계정입니다. 다른 이메일을 사용하세요.")
    elif "필수 정보" in str(e):
        print("인증에 필요한 정보를 모두 입력하세요.")
    else:
        print(f"입력 오류: {e}")
except Exception as e:
    print(f"시스템 오류: {e}")
```

## 의존성

유즈케이스 실행을 위해 필요한 의존성:

1. **AccountRepositoryPort**: 계정 데이터 저장/조회
2. **AuthConfigRepositoryPort**: 인증 설정 저장/조회  
3. **LoggerPort**: 로깅

## 완전한 사용 예제

```python
import asyncio
from adapters.db.database import initialize_database
from adapters.db.repositories import AccountRepositoryAdapter, AuthConfigRepositoryAdapter
from adapters.logger import create_logger
from config.adapters import get_config
from core.usecases.account_management import AccountManagementUseCase
from core.domain.entities import AuthType

async def main():
    # 설정 및 데이터베이스 초기화
    config = get_config()
    db_adapter = initialize_database(config)
    await db_adapter.initialize()
    
    try:
        async with db_adapter.get_session() as session:
            # Repository 어댑터 생성
            account_repo = AccountRepositoryAdapter(session)
            auth_config_repo = AuthConfigRepositoryAdapter(session)
            logger = create_logger("account_registration")
            
            # 유즈케이스 생성
            usecase = AccountManagementUseCase(
                account_repository=account_repo,
                auth_config_repository=auth_config_repo,
                logger=logger,
            )
            
            # 계정 등록
            account = await usecase.register_account(
                email="newuser@company.com",
                auth_type=AuthType.AUTHORIZATION_CODE,
                display_name="New User",
                tenant_id="tenant-123",
                client_id="client-456",
                client_secret="secret-789",
                redirect_uri="http://localhost:8080/callback"
            )
            
            print(f"계정 등록 완료!")
            print(f"ID: {account.id}")
            print(f"이메일: {account.email}")
            print(f"상태: {account.status.value}")
            
    finally:
        await db_adapter.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 주의사항

1. **비동기 처리**: 모든 메서드는 `async/await` 패턴을 사용합니다
2. **트랜잭션**: 계정과 인증 설정은 하나의 트랜잭션으로 처리됩니다
3. **초기 상태**: 등록된 계정의 초기 상태는 `INACTIVE`입니다
4. **보안**: 클라이언트 시크릿은 암호화되어 저장됩니다
5. **로깅**: 모든 중요한 작업은 로그로 기록됩니다

이 유즈케이스를 통해 Microsoft 365 계정을 안전하고 일관된 방식으로 시스템에 등록할 수 있습니다.
