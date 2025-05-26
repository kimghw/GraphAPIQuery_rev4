# 사용자 시나리오 및 유즈케이스

## 현재 구현된 유즈케이스 (1단계 완료)

### Atomic Usecases
- [x] **계정 등록**: Microsoft 365 계정을 시스템에 등록
- [x] **계정 조회**: 등록된 계정 목록 및 상세 정보 조회
- [x] **계정 업데이트**: 표시 이름, 인증 타입, 테넌트 ID 변경
- [x] **계정 삭제**: 계정 및 관련 인증 설정 완전 삭제

### Composite Usecases
- [x] **계정 관리 워크플로우**: 등록 → 조회 → 업데이트 → 삭제의 전체 생명주기

## 다음 단계 유즈케이스 (2단계: 인증 시스템)

### Atomic Usecases
- [ ] **OAuth 인증 시작**: Authorization Code Flow 시작
- [ ] **인증 코드 처리**: 콜백에서 받은 코드로 토큰 획득
- [ ] **Device Code 인증**: 디바이스 코드 플로우로 인증
- [ ] **토큰 저장**: 액세스/리프레시 토큰 암호화 저장
- [ ] **토큰 갱신**: 리프레시 토큰으로 액세스 토큰 갱신
- [ ] **인증 상태 확인**: 계정의 현재 인증 상태 확인
- [ ] **토큰 무효화**: 로그아웃 시 토큰 삭제

### Composite Usecases
- [ ] **완전한 인증 워크플로우**: 계정 등록 → 인증 → 토큰 저장 → 자동 갱신
- [ ] **재인증 워크플로우**: 토큰 만료 감지 → 자동 갱신 또는 재인증 요청

## 사용자 요구사항 변경 이력

### 최근 요구사항 (현재 적용)
- 사용자: "조회하고 등록하는 기능은 잘 된거 같아요. 유저 요구사항에 이를 반영하고 다음 task 로 넘어 갑니다."
- 상태: 1단계 완료, 2단계(인증 시스템) 진행 준비

### 시스템 제안 유즈케이스 (구현 대상 아님)
- **배치 인증**: 여러 계정 동시 인증 처리
- **인증 모니터링**: 토큰 만료 예정 알림
- **인증 로그**: 인증 시도 및 결과 로깅
- **보안 감사**: 비정상적인 인증 패턴 감지

## CLI 명령어 매핑

### 현재 구현된 명령어
```bash
# 계정 관리
python main.py account register <email> [옵션들]
python main.py account list [필터 옵션들]
python main.py account get --email <email> 또는 --account-id <uuid>
python main.py account update --email <email> [업데이트 옵션들]
python main.py account delete --email <email> [--force]
```

### 다음 단계 예상 명령어
```bash
# 인증 관리 (예상)
python main.py auth login --email <email> [--flow auth-code|device-code]
python main.py auth status --email <email>
python main.py auth refresh --email <email>
python main.py auth logout --email <email>
```

## 테스트 시나리오

### 완료된 테스트
- 계정 등록/조회/업데이트/삭제 기능 검증
- 실제 Azure 계정(kimghw@krs.co.kr) 등록 및 관리 성공

### 다음 단계 테스트 계획
- OAuth 2.0 인증 플로우 테스트
- 토큰 저장 및 암호화 테스트
- 토큰 자동 갱신 테스트
- 인증 상태 확인 테스트
