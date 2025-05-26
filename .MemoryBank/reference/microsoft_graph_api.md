# Microsoft Graph API 참조 문서

## 개요
Microsoft Graph API는 Microsoft 365, Windows 10, Enterprise Mobility + Security의 데이터와 인텔리전스에 액세스할 수 있는 통합 API 엔드포인트입니다.

## 기본 정보

### 베이스 URL
```
https://graph.microsoft.com/v1.0
https://graph.microsoft.com/beta  # 베타 버전
```

### 인증 방식
- **OAuth 2.0 Authorization Code Flow**: 웹 애플리케이션용
- **OAuth 2.0 Device Code Flow**: 브라우저 없는 환경용
- **Client Credentials Flow**: 애플리케이션 전용 (사용자 없음)

## OAuth 2.0 인증 플로우

### Authorization Code Flow

#### 1. 인증 URL 생성
```
GET https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize
```

**필수 매개변수**:
- `client_id`: 애플리케이션 ID
- `response_type`: "code"
- `redirect_uri`: 등록된 리디렉션 URI
- `scope`: 요청할 권한 범위
- `state`: CSRF 보호용 임의 값

**예시**:
```
https://login.microsoftonline.com/common/oauth2/v2.0/authorize?
client_id=12345678-1234-1234-1234-123456789012&
response_type=code&
redirect_uri=http://localhost:8000/auth/callback&
scope=https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.Send&
state=random_state_value
```

#### 2. 토큰 교환
```
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
```

**요청 본문** (application/x-www-form-urlencoded):
```
client_id=12345678-1234-1234-1234-123456789012
&client_secret=your_client_secret
&code=authorization_code_from_callback
&redirect_uri=http://localhost:8000/auth/callback
&grant_type=authorization_code
```

**응답**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "AwABAAAAvPM1KaPlrEqdFSBzjqfTGBCmLdgfSTLEMPGYuNHSUYBrq...",
  "scope": "https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.Send"
}
```

### Device Code Flow

#### 1. 디바이스 코드 요청
```
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode
```

**요청 본문**:
```
client_id=12345678-1234-1234-1234-123456789012
&scope=https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.Send
```

**응답**:
```json
{
  "user_code": "GFHKLMNOP",
  "device_code": "GMMhmHCXhWEzkobqIHGG_EnNYYsAkukHspeYUk9E8...",
  "verification_uri": "https://microsoft.com/devicelogin",
  "expires_in": 900,
  "interval": 5,
  "message": "To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code GFHKLMNOP to authenticate."
}
```

#### 2. 토큰 폴링
```
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
```

**요청 본문**:
```
grant_type=urn:ietf:params:oauth:grant-type:device_code
&client_id=12345678-1234-1234-1234-123456789012
&device_code=GMMhmHCXhWEzkobqIHGG_EnNYYsAkukHspeYUk9E8...
```

### 토큰 갱신
```
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
```

**요청 본문**:
```
client_id=12345678-1234-1234-1234-123456789012
&client_secret=your_client_secret
&refresh_token=AwABAAAAvPM1KaPlrEqdFSBzjqfTGBCmLdgfSTLEMPGYuNHSUYBrq...
&grant_type=refresh_token
```

## 주요 API 엔드포인트

### 사용자 정보
```
GET https://graph.microsoft.com/v1.0/me
```

### 메일 관련 API

#### 메일 목록 조회
```
GET https://graph.microsoft.com/v1.0/me/messages
```

**쿼리 매개변수**:
- `$select`: 반환할 필드 선택
- `$filter`: 필터 조건
- `$orderby`: 정렬 기준
- `$top`: 반환할 항목 수
- `$skip`: 건너뛸 항목 수

**예시**:
```
GET https://graph.microsoft.com/v1.0/me/messages?$select=subject,from,receivedDateTime&$top=10&$orderby=receivedDateTime desc
```

#### 특정 메일 조회
```
GET https://graph.microsoft.com/v1.0/me/messages/{message-id}
```

#### 메일 발송
```
POST https://graph.microsoft.com/v1.0/me/sendMail
```

**요청 본문**:
```json
{
  "message": {
    "subject": "메일 제목",
    "body": {
      "contentType": "Text",
      "content": "메일 내용"
    },
    "toRecipients": [
      {
        "emailAddress": {
          "address": "recipient@example.com"
        }
      }
    ]
  }
}
```

#### 메일 읽음 처리
```
PATCH https://graph.microsoft.com/v1.0/me/messages/{message-id}
```

**요청 본문**:
```json
{
  "isRead": true
}
```

#### 메일 삭제
```
DELETE https://graph.microsoft.com/v1.0/me/messages/{message-id}
```

## 권한 범위 (Scopes)

### 메일 관련 권한
- `https://graph.microsoft.com/Mail.Read`: 메일 읽기
- `https://graph.microsoft.com/Mail.ReadWrite`: 메일 읽기/쓰기
- `https://graph.microsoft.com/Mail.Send`: 메일 발송
- `https://graph.microsoft.com/MailboxSettings.Read`: 메일박스 설정 읽기

### 사용자 관련 권한
- `https://graph.microsoft.com/User.Read`: 사용자 프로필 읽기
- `https://graph.microsoft.com/User.ReadBasic.All`: 모든 사용자 기본 정보 읽기

## 에러 처리

### 일반적인 HTTP 상태 코드
- `200 OK`: 성공
- `201 Created`: 생성 성공
- `204 No Content`: 성공 (응답 본문 없음)
- `400 Bad Request`: 잘못된 요청
- `401 Unauthorized`: 인증 실패
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스 없음
- `429 Too Many Requests`: 요청 한도 초과

### 에러 응답 형식
```json
{
  "error": {
    "code": "InvalidRequest",
    "message": "The request is invalid",
    "innerError": {
      "date": "2023-05-26T12:00:00",
      "request-id": "12345678-1234-1234-1234-123456789012"
    }
  }
}
```

## 제한 사항 및 할당량

### 요청 제한
- **애플리케이션별**: 10,000 요청/10분
- **사용자별**: 1,000 요청/10분
- **테넌트별**: 20,000 요청/10분

### 배치 요청
- 최대 20개 요청을 하나의 배치로 처리 가능
- 배치 요청 크기 제한: 4MB

## 베스트 프랙티스

### 1. 토큰 관리
- 액세스 토큰은 1시간 후 만료
- 리프레시 토큰을 사용하여 자동 갱신
- 토큰을 안전하게 저장 (암호화)

### 2. 에러 처리
- 429 응답 시 Retry-After 헤더 확인
- 지수 백오프 재시도 구현
- 네트워크 오류에 대한 재시도 로직

### 3. 성능 최적화
- $select를 사용하여 필요한 필드만 요청
- 페이징을 사용하여 대량 데이터 처리
- 배치 요청으로 여러 API 호출 최적화

### 4. 보안
- HTTPS만 사용
- state 매개변수로 CSRF 공격 방지
- 클라이언트 시크릿 안전하게 보관

## 개발 도구

### Graph Explorer
- URL: https://developer.microsoft.com/graph/graph-explorer
- 브라우저에서 Graph API 테스트 가능

### Postman Collection
- Microsoft Graph API Postman 컬렉션 제공
- 인증 및 API 호출 예제 포함

### SDK
- **Python**: `msgraph-sdk-python`
- **JavaScript**: `@azure/msal-node`, `@microsoft/microsoft-graph-client`
- **.NET**: `Microsoft.Graph`

## 참고 링크
- [Microsoft Graph 문서](https://docs.microsoft.com/graph/)
- [Graph Explorer](https://developer.microsoft.com/graph/graph-explorer)
- [Azure AD 앱 등록](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
- [권한 참조](https://docs.microsoft.com/graph/permissions-reference)
