# 데이터베이스 인덱스 설계

Microsoft Graph API Query 프로젝트의 데이터베이스 성능 최적화를 위한 인덱스 설계 문서입니다.

## 개요

성능 최적화를 위해 자주 사용되는 쿼리 패턴에 맞춰 단일 인덱스와 복합 인덱스를 설계했습니다.

## 테이블별 인덱스

### 1. accounts 테이블

#### 단일 인덱스
- `email` (UNIQUE): 이메일로 계정 조회
- `auth_type`: 인증 타입별 필터링
- `status`: 상태별 필터링
- `last_sync_at`: 동기화 시간 기준 정렬
- `created_at`: 생성일 기준 정렬
- `updated_at`: 수정일 기준 정렬

#### 복합 인덱스
- `idx_accounts_status_auth_type (status, auth_type)`: 상태와 인증 타입 조합 필터링
- `idx_accounts_email_status (email, status)`: 이메일과 상태 조합 조회
- `idx_accounts_created_status (created_at, status)`: 생성일과 상태 조합 정렬
- `idx_accounts_last_sync_status (last_sync_at, status)`: 동기화 시간과 상태 조합

### 2. auth_code_configs 테이블

#### 단일 인덱스
- `client_id`: 클라이언트 ID로 조회
- `tenant_id`: 테넌트 ID로 조회
- `created_at`: 생성일 기준 정렬

#### 복합 인덱스
- `idx_auth_code_client_tenant (client_id, tenant_id)`: 클라이언트와 테넌트 조합 조회

### 3. device_code_configs 테이블

#### 단일 인덱스
- `client_id`: 클라이언트 ID로 조회
- `tenant_id`: 테넌트 ID로 조회
- `created_at`: 생성일 기준 정렬

#### 복합 인덱스
- `idx_device_code_client_tenant (client_id, tenant_id)`: 클라이언트와 테넌트 조합 조회

### 4. tokens 테이블

#### 단일 인덱스
- `expires_at`: 만료 시간 기준 조회 (토큰 갱신 시)
- `created_at`: 생성일 기준 정렬

#### 복합 인덱스
- `idx_tokens_account_expires (account_id, expires_at)`: 계정별 토큰 만료 시간 조회
- `idx_tokens_expires_created (expires_at, created_at)`: 만료 시간과 생성일 조합

### 5. mails 테이블

#### 단일 인덱스
- `account_id`: 계정별 메일 조회
- `message_id`: Graph API 메시지 ID로 조회
- `sender`: 발신자별 메일 조회
- `importance`: 중요도별 필터링
- `is_read`: 읽음 상태별 필터링
- `has_attachments`: 첨부파일 여부별 필터링
- `received_at`: 수신일 기준 정렬
- `sent_at`: 발송일 기준 정렬
- `processed_at`: 처리일 기준 정렬
- `created_at`: 생성일 기준 정렬

#### 복합 인덱스
- `idx_mails_account_received (account_id, received_at)`: 계정별 수신일 정렬
- `idx_mails_account_processed (account_id, processed_at)`: 계정별 처리일 정렬
- `idx_mails_account_read (account_id, is_read)`: 계정별 읽음 상태
- `idx_mails_sender_received (sender, received_at)`: 발신자별 수신일 정렬
- `idx_mails_message_account (message_id, account_id)`: 메시지 ID와 계정 조합
- `idx_mails_received_read (received_at, is_read)`: 수신일과 읽음 상태 조합
- `idx_mails_importance_received (importance, received_at)`: 중요도와 수신일 조합
- `idx_mails_attachments_received (has_attachments, received_at)`: 첨부파일과 수신일 조합

### 6. sync_histories 테이블

#### 단일 인덱스
- `account_id`: 계정별 동기화 이력 조회
- `sync_type`: 동기화 타입별 필터링
- `status`: 상태별 필터링
- `started_at`: 시작일 기준 정렬
- `completed_at`: 완료일 기준 정렬
- `created_at`: 생성일 기준 정렬

#### 복합 인덱스
- `idx_sync_account_started (account_id, started_at)`: 계정별 시작일 정렬
- `idx_sync_account_status (account_id, status)`: 계정별 상태 필터링
- `idx_sync_type_status (sync_type, status)`: 타입과 상태 조합
- `idx_sync_started_status (started_at, status)`: 시작일과 상태 조합
- `idx_sync_completed_status (completed_at, status)`: 완료일과 상태 조합

### 7. delta_links 테이블

#### 단일 인덱스
- `last_sync_at`: 마지막 동기화 시간 기준 조회
- `created_at`: 생성일 기준 정렬

### 8. webhook_subscriptions 테이블

#### 단일 인덱스
- `account_id`: 계정별 구독 조회
- `subscription_id` (UNIQUE): Graph API 구독 ID로 조회
- `resource`: 리소스별 구독 조회
- `expires_at`: 만료일 기준 조회
- `is_active`: 활성 상태별 필터링
- `created_at`: 생성일 기준 정렬

#### 복합 인덱스
- `idx_webhook_account_active (account_id, is_active)`: 계정별 활성 구독
- `idx_webhook_expires_active (expires_at, is_active)`: 만료일과 활성 상태 조합
- `idx_webhook_resource_active (resource, is_active)`: 리소스와 활성 상태 조합
- `idx_webhook_subscription_active (subscription_id, is_active)`: 구독 ID와 활성 상태 조합

## 쿼리 최적화 효과

### 주요 쿼리 패턴과 활용 인덱스

1. **계정 조회**
   - `SELECT * FROM accounts WHERE email = ?` → `email` 인덱스
   - `SELECT * FROM accounts WHERE status = 'active'` → `status` 인덱스
   - `SELECT * FROM accounts WHERE status = ? AND auth_type = ?` → `idx_accounts_status_auth_type`

2. **메일 조회**
   - `SELECT * FROM mails WHERE account_id = ? ORDER BY received_at DESC` → `idx_mails_account_received`
   - `SELECT * FROM mails WHERE account_id = ? AND is_read = false` → `idx_mails_account_read`
   - `SELECT * FROM mails WHERE sender = ? ORDER BY received_at DESC` → `idx_mails_sender_received`

3. **동기화 이력**
   - `SELECT * FROM sync_histories WHERE account_id = ? ORDER BY started_at DESC` → `idx_sync_account_started`
   - `SELECT * FROM sync_histories WHERE account_id = ? AND status = 'success'` → `idx_sync_account_status`

4. **토큰 관리**
   - `SELECT * FROM tokens WHERE account_id = ? AND expires_at > NOW()` → `idx_tokens_account_expires`
   - `SELECT * FROM tokens WHERE expires_at < NOW()` → `expires_at` 인덱스

5. **웹훅 구독**
   - `SELECT * FROM webhook_subscriptions WHERE account_id = ? AND is_active = true` → `idx_webhook_account_active`
   - `SELECT * FROM webhook_subscriptions WHERE expires_at < NOW() AND is_active = true` → `idx_webhook_expires_active`

## 성능 모니터링

### 인덱스 효과 측정 방법

1. **SQLite EXPLAIN QUERY PLAN 사용**
   ```sql
   EXPLAIN QUERY PLAN SELECT * FROM accounts WHERE status = 'active' AND auth_type = 'authorization_code';
   ```

2. **쿼리 실행 시간 측정**
   - 인덱스 적용 전후 비교
   - 대용량 데이터에서의 성능 테스트

3. **인덱스 사용률 모니터링**
   - 실제 운영 환경에서의 쿼리 패턴 분석
   - 사용되지 않는 인덱스 식별

## 주의사항

1. **인덱스 오버헤드**
   - INSERT/UPDATE/DELETE 시 인덱스 유지 비용
   - 저장 공간 사용량 증가

2. **인덱스 선택성**
   - 카디널리티가 낮은 컬럼의 인덱스 효과 제한
   - 복합 인덱스의 컬럼 순서 중요성

3. **정기적인 인덱스 최적화**
   - SQLite VACUUM 명령으로 인덱스 재구성
   - 쿼리 패턴 변화에 따른 인덱스 재검토

## 향후 개선 방안

1. **파티셔닝 고려**
   - 대용량 메일 데이터의 날짜별 파티셔닝
   - 계정별 데이터 분산

2. **추가 인덱스 검토**
   - 실제 사용 패턴에 따른 인덱스 추가
   - 부분 인덱스(Partial Index) 활용

3. **데이터베이스 엔진 고려**
   - PostgreSQL 마이그레이션 시 인덱스 최적화
   - 전문 검색을 위한 Full-Text Search 인덱스
