# Microsoft 365 인증 설정 가이드

Microsoft 365 Graph API를 사용하기 위한 완전한 인증 설정 가이드입니다.

## 🚀 1단계: Azure AD 앱 등록

### Azure Portal에서 앱 등록

1. **Azure Portal 접속**
   - https://portal.azure.com 접속
   - Microsoft 365 관리자 계정으로 로그인

2. **Azure Active Directory 선택**
   - 좌측 메뉴에서 "Azure Active Directory" 클릭

3. **앱 등록**
   - "앱 등록" → "새 등록" 클릭
   - 앱 이름: `GraphAPIQuery` (또는 원하는 이름)
   - 지원되는 계정 유형: "이 조직 디렉터리의 계정만"
   - 리디렉션 URI: 나중에 설정

### 앱 설정 구성

4. **인증 설정**
   ```
   플랫폼 추가 → 웹
   리디렉션 URI: http://localhost:8080/auth/callback
   
   플랫폼 추가 → 모바일 및 데스크톱 애플리케이션
   리디렉션 URI: https://login.microsoftonline.com/common/oauth2/nativeclient
   ```

5. **API 권한 설정**
   ```
   Microsoft Graph → 위임된 권한:
   - Mail.Read (메일 읽기)
   - Mail.Send (메일 보내기)
   - Mail.ReadWrite (메일 읽기/쓰기)
   - User.Read (사용자 프로필 읽기)
   - offline_access (리프레시 토큰)
   
   관리자 동의 부여 클릭
   ```

6. **클라이언트 시크릿 생성**
   - "인증서 및 비밀" → "새 클라이언트 비밀"
   - 설명: `GraphAPIQuery Secret`
   - 만료: 24개월
   - **⚠️ 생성된 값을 즉시 복사하여 저장**

## 🔧 2단계: 환경 설정

### .env 파일 업데이트

```bash
# Microsoft Graph API 설정 (실제 값으로 교체)
AZURE_CLIENT_ID=your_actual_client_id_here
AZURE_CLIENT_SECRET=your_actual_client_secret_here
AZURE_TENANT_ID=your_actual_tenant_id_here

# OAuth 설정
OAUTH_REDIRECT_URI=http://localhost:8080/auth/callback
OAUTH_STATE_SECRET=your_secure_random_32_byte_key

# 암호화 설정 (32바이트 키)
ENCRYPTION_KEY=your_secure_encryption_key_32_bytes!
```

### 필수 정보 확인

Azure Portal에서 다음 정보를 복사:

1. **애플리케이션(클라이언트) ID** → `AZURE_CLIENT_ID`
2. **디렉터리(테넌트) ID** → `AZURE_TENANT_ID`  
3. **클라이언트 시크릿 값** → `AZURE_CLIENT_SECRET`

## 🔐 3단계: 인증 절차

### Authorization Code Flow (웹 애플리케이션용)

**1. 계정 등록 및 설정**
```bash
# 계정 등록 (Authorization Code Flow)
python main.py account register kimghw@krs.co.kr \
  --display-name "KRS User" \
  --auth-type authorization_code \
  --client-id your_actual_client_id \
  --client-secret your_actual_client_secret \
  --redirect-uri http://localhost:8080/auth/callback \
  --tenant-id your_actual_tenant_id
```

**2. 인증 시작**
```bash
python main.py auth start-auth-code --email kimghw@krs.co.kr
```

출력 예시:
```
🔐 Authorization Code Flow

계정: kimghw@krs.co.kr
State: abc123def456

다음 URL로 이동하여 인증을 완료하세요:
https://login.microsoftonline.com/your-tenant/oauth2/v2.0/authorize?...

인증 완료 후 받은 코드로 다음 명령어를 실행하세요:
python main.py auth complete-auth-code --code <CODE> --state abc123def456
```

**3. 브라우저에서 인증**
- 제공된 URL을 브라우저에서 열기
- Microsoft 계정으로 로그인
- 권한 승인
- 리디렉션 URL에서 `code` 파라미터 복사

**4. 인증 완료**
```bash
python main.py auth complete-auth-code \
  --code M.R3_BAY.CdTS_... \
  --state abc123def456
```

### Device Code Flow (CLI/헤드리스용)

**1. 계정 등록 및 설정**
```bash
# 계정 등록 (Device Code Flow)
python main.py account register kimghw@krs.co.kr \
  --display-name "KRS User" \
  --auth-type device_code \
  --client-id your_actual_client_id \
  --tenant-id your_actual_tenant_id
```

**2. 인증 시작**
```bash
python main.py auth start-device-code --email kimghw@krs.co.kr
```

출력 예시:
```
📱 Device Code Flow

계정: kimghw@krs.co.kr
사용자 코드: ABCD-EFGH
디바이스 코드: device_code_value

다음 URL로 이동하여 사용자 코드를 입력하세요:
https://microsoft.com/devicelogin

인증 완료를 기다리려면 다음 명령어를 실행하세요:
python main.py auth poll-device-code --device-code device_code_value
```

**3. 브라우저에서 인증**
- https://microsoft.com/devicelogin 접속
- 사용자 코드 입력 (예: ABCD-EFGH)
- Microsoft 계정으로 로그인
- 권한 승인

**4. 인증 완료 대기**
```bash
python main.py auth poll-device-code --device-code device_code_value
```

## 🔄 4단계: 토큰 관리

### 토큰 상태 확인
```bash
# 만료 임박 토큰 확인 및 자동 갱신
python main.py auth check-tokens --minutes 5

# 수동 토큰 갱신
python main.py auth refresh-token --email kimghw@krs.co.kr
```

### 사용자 프로필 확인
```bash
# 인증 성공 확인
python main.py auth get-profile --email kimghw@krs.co.kr
```

## ⚠️ 필수 준비사항

### 1. Azure AD 앱 등록 정보
- ✅ 애플리케이션(클라이언트) ID
- ✅ 디렉터리(테넌트) ID
- ✅ 클라이언트 시크릿 (Authorization Code Flow용)

### 2. API 권한 승인
- ✅ Mail.Read
- ✅ Mail.Send  
- ✅ Mail.ReadWrite
- ✅ User.Read
- ✅ offline_access
- ✅ 관리자 동의 완료

### 3. 리디렉션 URI 설정
- ✅ 웹: `http://localhost:8080/auth/callback`
- ✅ 모바일/데스크톱: `https://login.microsoftonline.com/common/oauth2/nativeclient`

## 🚨 보안 주의사항

### 환경 변수 보안
```bash
# 실제 운영 환경에서는 안전한 키 생성
openssl rand -hex 32  # ENCRYPTION_KEY용
openssl rand -hex 32  # OAUTH_STATE_SECRET용
```

### 클라이언트 시크릿 관리
- 절대 코드에 하드코딩하지 말 것
- 환경 변수나 Azure Key Vault 사용
- 정기적으로 시크릿 갱신

### 토큰 보안
- 모든 토큰은 AES-256으로 암호화 저장
- 리프레시 토큰은 안전하게 보관
- 불필요한 토큰은 즉시 폐기

## 🔍 문제 해결

### 일반적인 오류

**1. "invalid_client" 오류**
- 클라이언트 ID/시크릿 확인
- 테넌트 ID 확인
- Azure AD 앱 등록 상태 확인

**2. "invalid_grant" 오류**
- 인증 코드 만료 (10분 제한)
- 리디렉션 URI 불일치
- 시간 동기화 문제

**3. "insufficient_scope" 오류**
- API 권한 설정 확인
- 관리자 동의 여부 확인
- 권한 범위 재설정

### 디버깅 명령어
```bash
# 계정 상태 확인
python main.py account get --email kimghw@krs.co.kr

# 로그 레벨 증가
LOG_LEVEL=DEBUG python main.py auth start-auth-code --email kimghw@krs.co.kr
```

## 📚 추가 리소스

- [Microsoft Graph API 문서](https://docs.microsoft.com/graph/)
- [Azure AD 앱 등록 가이드](https://docs.microsoft.com/azure/active-directory/develop/quickstart-register-app)
- [OAuth 2.0 플로우 설명](https://docs.microsoft.com/azure/active-directory/develop/v2-oauth2-auth-code-flow)

이 가이드를 따라하면 Microsoft 365와 완전히 연동된 인증 시스템을 구축할 수 있습니다.
