# 인증 시스템 가이드

Microsoft 365 Graph API 인증 시스템 사용 가이드입니다.

## 개요

이 시스템은 Microsoft 365 Graph API에 접근하기 위한 OAuth 2.0 인증을 지원합니다.
두 가지 인증 플로우를 제공합니다:

1. **Authorization Code Flow**: 웹 애플리케이션용
2. **Device Code Flow**: CLI 및 헤드리스 애플리케이션용

## 사전 준비

### Azure AD 앱 등록

1. [Azure Portal](https://portal.azure.com)에 로그인
2. Azure Active Directory > 앱 등록 > 새 등록
3. 애플리케이션 정보 입력:
   - 이름: Graph API Query App
   - 지원되는 계정 유형: 조직 디렉터리의 계정만
   - 리디렉션 URI: `http://localhost:8080/auth/callback` (Authorization Code Flow용)

### 권한 설정

Microsoft Graph API 권한 추가:
- `Mail.Read`: 메일 읽기
- `Mail.Send`: 메일 발송
- `User.Read`: 사용자 프로필 읽기
- `offline_access`: 리프레시 토큰 사용

### 환경 변수 설정

`.env` 파일에 Azure 앱 정보 설정:

```bash
AZURE_CLIENT_ID=your_client_id_here
AZURE_CLIENT_SECRET=your_client_secret_here  # Authorization Code Flow용
AZURE_TENANT_ID=your_tenant_id_here
ENCRYPTION_KEY=your_32_byte_encryption_key_here_12345
```

## 계정 등록

먼저 시스템에 Microsoft 365 계정을 등록해야 합니다:

### Authorization Code Flow 계정 등록

```bash
python main.py account register user@company.com \
  --display-name "사용자 이름" \
  --auth-type authorization_code \
  --client-id your_client_id \
  --client-secret your_client_secret \
  --tenant-id your_tenant_id \
  --redirect-uri http://localhost:8080/auth/callback
```

### Device Code Flow 계정 등록

```bash
python main.py account register user@company.com \
  --display-name "사용자 이름" \
  --auth-type device_code \
  --client-id your_client_id \
  --tenant-id your_tenant_id
```

## 인증 플로우

### Authorization Code Flow

1. **인증 시작**:
   ```bash
   python main.py auth start-auth-code --email user@company.com
   ```

2. 출력된 URL로 이동하여 로그인

3. **인증 완료**:
   ```bash
   python main.py auth complete-auth-code --code <받은_코드> --state <받은_상태값>
   ```

### Device Code Flow

1. **인증 시작**:
   ```bash
   python main.py auth start-device-code --email user@company.com
   ```

2. 출력된 URL로 이동하여 사용자 코드 입력

3. **인증 폴링**:
   ```bash
   python main.py auth poll-device-code --device-code <디바이스_코드>
   ```

## 토큰 관리

### 토큰 갱신

```bash
python main.py auth refresh-token --email user@company.com
```

### 만료 임박 토큰 자동 갱신

```bash
python main.py auth check-tokens --minutes 5
```

### 토큰 폐기

```bash
python main.py auth revoke-token --email user@company.com
```

## 사용자 프로필 조회

인증된 계정의 프로필 정보를 조회할 수 있습니다:

```bash
python main.py auth get-profile --email user@company.com
```

## 보안 고려사항

### 토큰 암호화

- 모든 토큰은 AES-256 암호화되어 저장됩니다
- 암호화 키는 환경 변수로 관리됩니다
- 32바이트 길이의 강력한 암호화 키를 사용하세요

### 토큰 만료 관리

- Access Token: 1시간 유효
- Refresh Token: 90일 유효 (사용 시 갱신)
- 자동 갱신 기능으로 토큰 만료 방지

### 캐시 보안

- 인증 상태는 Redis 또는 메모리 캐시에 임시 저장
- 민감한 정보는 암호화하여 캐시

## 문제 해결

### 일반적인 오류

1. **invalid_client**: 클라이언트 ID/Secret 확인
2. **invalid_grant**: 인증 코드 만료 또는 잘못된 코드
3. **access_denied**: 사용자가 권한 거부
4. **expired_token**: 토큰 만료, 갱신 필요

### 디버깅

로그 레벨을 DEBUG로 설정하여 상세 정보 확인:

```bash
export LOG_LEVEL=DEBUG
python main.py auth start-device-code --email user@company.com
```

### 토큰 상태 확인

```bash
python main.py account get --email user@company.com
```

## API 사용 예제

인증 완료 후 Graph API 호출:

```python
from adapters.factory import get_adapter_factory
from adapters.db.database import get_async_session

async def get_user_messages():
    factory = get_adapter_factory()
    
    async with get_async_session() as session:
        auth_usecase = factory.create_authentication_usecase(session)
        
        # 사용자 프로필 조회
        profile = await auth_usecase.get_user_profile(account_id)
        
        # Graph API 클라이언트로 메시지 조회
        graph_client = factory.create_graph_api_client()
        token = await auth_usecase.get_valid_token(account_id)
        
        messages = await graph_client.list_messages(
            access_token=token.access_token,
            top=10
        )
        
        return messages
```

## 자동화

### 토큰 자동 갱신 스케줄링

cron 작업으로 토큰 자동 갱신:

```bash
# 매 시간마다 만료 임박 토큰 갱신
0 * * * * cd /path/to/project && python main.py auth check-tokens --minutes 5
```

### 배치 인증

여러 계정을 한 번에 인증:

```bash
#!/bin/bash
accounts=("user1@company.com" "user2@company.com" "user3@company.com")

for account in "${accounts[@]}"; do
    echo "Processing $account..."
    python main.py auth refresh-token --email "$account"
done
```

## 모니터링

### 인증 상태 모니터링

```bash
# 모든 계정의 토큰 상태 확인
python main.py account list --status active

# 특정 계정의 상세 정보
python main.py account get --email user@company.com
```

### 로그 모니터링

인증 관련 로그는 다음과 같은 패턴으로 기록됩니다:

```
2024-01-01 12:00:00 - GraphAPIQuery - INFO - 토큰 갱신 성공: user@company.com
2024-01-01 12:00:01 - GraphAPIQuery - WARNING - 토큰 만료 임박: user@company.com (5분 남음)
2024-01-01 12:00:02 - GraphAPIQuery - ERROR - 토큰 갱신 실패: user@company.com - invalid_grant
```

## 참고 자료

- [Microsoft Graph API 문서](https://docs.microsoft.com/en-us/graph/)
- [OAuth 2.0 Authorization Code Flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [OAuth 2.0 Device Code Flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code)
- [Microsoft Graph 권한 참조](https://docs.microsoft.com/en-us/graph/permissions-reference)
