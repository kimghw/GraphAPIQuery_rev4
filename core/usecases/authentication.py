"""
인증 유즈케이스

Microsoft 365 OAuth 2.0 인증 처리를 위한 비즈니스 로직을 구현합니다.
- Authorization Code Flow
- Device Code Flow
- 토큰 갱신 및 관리
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from uuid import UUID

from ..domain.entities import (
    Account,
    AuthCodeConfig,
    AuthType,
    DeviceCodeConfig,
    Token,
)
from ..domain.ports import (
    AccountRepositoryPort,
    AuthConfigRepositoryPort,
    CacheServicePort,
    EncryptionServicePort,
    GraphApiClientPort,
    LoggerPort,
    TokenRepositoryPort,
)


class AuthenticationUseCase:
    """인증 유즈케이스"""
    
    def __init__(
        self,
        account_repository: AccountRepositoryPort,
        auth_config_repository: AuthConfigRepositoryPort,
        token_repository: TokenRepositoryPort,
        graph_api_client: GraphApiClientPort,
        encryption_service: EncryptionServicePort,
        cache_service: CacheServicePort,
        logger: LoggerPort,
    ):
        self.account_repository = account_repository
        self.auth_config_repository = auth_config_repository
        self.token_repository = token_repository
        self.graph_api_client = graph_api_client
        self.encryption_service = encryption_service
        self.cache_service = cache_service
        self.logger = logger
    
    async def start_authorization_code_flow(
        self,
        account_id: UUID,
        scope: str = "https://graph.microsoft.com/.default offline_access",
    ) -> Tuple[str, str]:
        """
        Authorization Code Flow 인증을 시작합니다.
        
        Args:
            account_id: 계정 ID
            scope: 요청할 권한 범위
            
        Returns:
            (authorization_url, state) 튜플
            
        Raises:
            ValueError: 계정이 존재하지 않거나 Authorization Code Flow가 아닌 경우
        """
        self.logger.info(f"Authorization Code Flow 시작: {account_id}")
        
        # 계정 조회
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            raise ValueError(f"계정을 찾을 수 없습니다: {account_id}")
        
        if account.auth_type != AuthType.AUTHORIZATION_CODE:
            raise ValueError(f"Authorization Code Flow가 아닙니다: {account.auth_type}")
        
        # 인증 설정 조회
        auth_config = await self.auth_config_repository.get_auth_code_config(account_id)
        if not auth_config:
            raise ValueError(f"인증 설정을 찾을 수 없습니다: {account_id}")
        
        # State 생성 및 캐시 저장
        import secrets
        state = secrets.token_urlsafe(32)
        cache_key = f"auth_state:{state}"
        await self.cache_service.set(
            cache_key,
            str(account_id),
            expire=600  # 10분
        )
        
        # 인증 URL 생성
        authorization_url = await self.graph_api_client.get_authorization_url(
            client_id=auth_config.client_id,
            tenant_id=auth_config.tenant_id,
            redirect_uri=auth_config.redirect_uri,
            scope=scope,
            state=state,
        )
        
        self.logger.info(f"Authorization Code Flow URL 생성 완료: {account_id}")
        return authorization_url, state
    
    async def complete_authorization_code_flow(
        self,
        code: str,
        state: str,
        scope: str = "https://graph.microsoft.com/.default offline_access",
    ) -> Token:
        """
        Authorization Code Flow 인증을 완료합니다.
        
        Args:
            code: 인증 코드
            state: State 값
            scope: 권한 범위
            
        Returns:
            생성된 토큰 엔티티
            
        Raises:
            ValueError: 유효하지 않은 state이거나 토큰 교환에 실패한 경우
        """
        self.logger.info(f"Authorization Code Flow 완료 시작: state={state}")
        
        # State 검증
        cache_key = f"auth_state:{state}"
        cached_account_id = await self.cache_service.get(cache_key)
        if not cached_account_id:
            raise ValueError("유효하지 않은 state입니다")
        
        account_id = UUID(cached_account_id)
        
        # State 캐시 삭제
        await self.cache_service.delete(cache_key)
        
        # 계정 및 인증 설정 조회
        account = await self.account_repository.get_by_id(account_id)
        auth_config = await self.auth_config_repository.get_auth_code_config(account_id)
        
        if not account or not auth_config:
            raise ValueError("계정 또는 인증 설정을 찾을 수 없습니다")
        
        # 토큰 교환
        token_response = await self.graph_api_client.exchange_code_for_token(
            client_id=auth_config.client_id,
            client_secret=auth_config.client_secret,
            tenant_id=auth_config.tenant_id,
            redirect_uri=auth_config.redirect_uri,
            code=code,
        )
        
        # 토큰 저장
        token = await self._save_token(account_id, token_response, scope)
        
        # 계정 활성화
        account.activate()
        await self.account_repository.update(account)
        
        self.logger.info(f"Authorization Code Flow 완료: {account_id}")
        return token
    
    async def start_device_code_flow(
        self,
        account_id: UUID,
        scope: str = "https://graph.microsoft.com/.default offline_access",
    ) -> Dict[str, str]:
        """
        Device Code Flow 인증을 시작합니다.
        
        Args:
            account_id: 계정 ID
            scope: 요청할 권한 범위
            
        Returns:
            디바이스 코드 정보 딕셔너리
            
        Raises:
            ValueError: 계정이 존재하지 않거나 Device Code Flow가 아닌 경우
        """
        self.logger.info(f"Device Code Flow 시작: {account_id}")
        
        # 계정 조회
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            raise ValueError(f"계정을 찾을 수 없습니다: {account_id}")
        
        if account.auth_type != AuthType.DEVICE_CODE:
            raise ValueError(f"Device Code Flow가 아닙니다: {account.auth_type}")
        
        # 인증 설정 조회
        auth_config = await self.auth_config_repository.get_device_code_config(account_id)
        if not auth_config:
            raise ValueError(f"인증 설정을 찾을 수 없습니다: {account_id}")
        
        # 디바이스 코드 요청
        device_code_response = await self.graph_api_client.get_device_code(
            client_id=auth_config.client_id,
            tenant_id=auth_config.tenant_id,
            scope=scope,
        )
        
        # 디바이스 코드 정보 캐시 저장
        cache_key = f"device_code:{device_code_response['device_code']}"
        await self.cache_service.set(
            cache_key,
            str(account_id),
            expire=device_code_response.get('expires_in', 900)  # 기본 15분
        )
        
        self.logger.info(f"Device Code Flow 시작 완료: {account_id}")
        return device_code_response
    
    async def poll_device_code_flow(
        self,
        device_code: str,
        scope: str = "https://graph.microsoft.com/.default offline_access",
        max_attempts: int = 60,
        interval: int = 5,
    ) -> Token:
        """
        Device Code Flow 인증을 폴링하여 완료합니다.
        
        Args:
            device_code: 디바이스 코드
            scope: 권한 범위
            max_attempts: 최대 시도 횟수
            interval: 폴링 간격 (초)
            
        Returns:
            생성된 토큰 엔티티
            
        Raises:
            ValueError: 유효하지 않은 디바이스 코드이거나 인증 실패
            TimeoutError: 인증 시간 초과
        """
        self.logger.info(f"Device Code Flow 폴링 시작: {device_code}")
        
        # 캐시에서 계정 ID 조회
        cache_key = f"device_code:{device_code}"
        cached_account_id = await self.cache_service.get(cache_key)
        if not cached_account_id:
            raise ValueError("유효하지 않은 디바이스 코드입니다")
        
        account_id = UUID(cached_account_id)
        
        # 계정 및 인증 설정 조회
        account = await self.account_repository.get_by_id(account_id)
        auth_config = await self.auth_config_repository.get_device_code_config(account_id)
        
        if not account or not auth_config:
            raise ValueError("계정 또는 인증 설정을 찾을 수 없습니다")
        
        # 폴링 시작
        for attempt in range(max_attempts):
            try:
                self.logger.debug(f"Device Code 폴링 시도 {attempt + 1}/{max_attempts}")
                
                token_response = await self.graph_api_client.poll_device_code(
                    client_id=auth_config.client_id,
                    tenant_id=auth_config.tenant_id,
                    device_code=device_code,
                )
                
                # 성공 시 토큰 저장
                token = await self._save_token(account_id, token_response, scope)
                
                # 디바이스 코드 캐시 삭제
                await self.cache_service.delete(cache_key)
                
                # 계정 활성화
                account.activate()
                await self.account_repository.update(account)
                
                self.logger.info(f"Device Code Flow 완료: {account_id}")
                return token
                
            except Exception as e:
                error_msg = str(e)
                
                # 사용자가 아직 인증하지 않은 경우 계속 폴링
                if "authorization_pending" in error_msg.lower():
                    await asyncio.sleep(interval)
                    continue
                
                # 사용자가 인증을 거부한 경우
                if "access_denied" in error_msg.lower():
                    await self.cache_service.delete(cache_key)
                    raise ValueError("사용자가 인증을 거부했습니다")
                
                # 디바이스 코드가 만료된 경우
                if "expired_token" in error_msg.lower():
                    await self.cache_service.delete(cache_key)
                    raise ValueError("디바이스 코드가 만료되었습니다")
                
                # 기타 오류
                self.logger.error(f"Device Code 폴링 오류: {error_msg}")
                await asyncio.sleep(interval)
        
        # 최대 시도 횟수 초과
        await self.cache_service.delete(cache_key)
        raise TimeoutError("Device Code 인증 시간이 초과되었습니다")
    
    async def refresh_token(self, account_id: UUID) -> Optional[Token]:
        """
        토큰을 갱신합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            갱신된 토큰 엔티티 또는 None
        """
        self.logger.info(f"토큰 갱신 시작: {account_id}")
        
        # 기존 토큰 조회
        existing_token = await self.token_repository.get_by_account_id(account_id)
        if not existing_token or not existing_token.can_refresh():
            self.logger.warning(f"갱신할 수 없는 토큰: {account_id}")
            return None
        
        # 계정 및 인증 설정 조회
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            self.logger.warning(f"계정을 찾을 수 없음: {account_id}")
            return None
        
        try:
            if account.auth_type == AuthType.AUTHORIZATION_CODE:
                auth_config = await self.auth_config_repository.get_auth_code_config(account_id)
                if not auth_config:
                    return None
                
                # 리프레시 토큰 복호화
                decrypted_refresh_token = await self.encryption_service.decrypt(
                    existing_token.refresh_token
                )
                
                # 토큰 갱신 요청
                token_response = await self.graph_api_client.refresh_token(
                    client_id=auth_config.client_id,
                    client_secret=auth_config.client_secret,
                    tenant_id=auth_config.tenant_id,
                    refresh_token=decrypted_refresh_token,
                )
                
            elif account.auth_type == AuthType.DEVICE_CODE:
                auth_config = await self.auth_config_repository.get_device_code_config(account_id)
                if not auth_config:
                    return None
                
                # 리프레시 토큰 복호화
                decrypted_refresh_token = await self.encryption_service.decrypt(
                    existing_token.refresh_token
                )
                
                # Device Code Flow에서는 client_secret 없이 갱신
                token_response = await self.graph_api_client.refresh_token(
                    client_id=auth_config.client_id,
                    client_secret=None,
                    tenant_id=auth_config.tenant_id,
                    refresh_token=decrypted_refresh_token,
                )
            
            else:
                self.logger.error(f"지원하지 않는 인증 타입: {account.auth_type}")
                return None
            
            # 새 토큰 저장
            new_token = await self._save_token(
                account_id,
                token_response,
                existing_token.scope
            )
            
            self.logger.info(f"토큰 갱신 완료: {account_id}")
            return new_token
            
        except Exception as e:
            self.logger.error(f"토큰 갱신 실패: {account_id}, 오류: {str(e)}")
            
            # 갱신 실패 시 계정을 오류 상태로 표시
            account.mark_error()
            await self.account_repository.update(account)
            
            return None
    
    async def revoke_token(self, account_id: UUID) -> bool:
        """
        토큰을 폐기합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            폐기 성공 여부
        """
        self.logger.info(f"토큰 폐기: {account_id}")
        
        # 토큰 삭제
        success = await self.token_repository.delete(account_id)
        
        if success:
            # 계정 비활성화
            account = await self.account_repository.get_by_id(account_id)
            if account:
                account.deactivate()
                await self.account_repository.update(account)
            
            self.logger.info(f"토큰 폐기 완료: {account_id}")
        else:
            self.logger.error(f"토큰 폐기 실패: {account_id}")
        
        return success
    
    async def get_user_profile(self, account_id: UUID) -> Optional[Dict]:
        """
        사용자 프로필을 조회합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            사용자 프로필 정보 또는 None
        """
        self.logger.debug(f"사용자 프로필 조회: {account_id}")
        
        # 토큰 조회
        token = await self.token_repository.get_by_account_id(account_id)
        if not token:
            return None
        
        # 토큰 만료 확인 및 갱신
        if token.is_expired():
            token = await self.refresh_token(account_id)
            if not token:
                return None
        
        try:
            # 액세스 토큰 복호화
            decrypted_access_token = await self.encryption_service.decrypt(
                token.access_token
            )
            
            # 사용자 프로필 조회
            profile = await self.graph_api_client.get_user_profile(decrypted_access_token)
            
            self.logger.debug(f"사용자 프로필 조회 완료: {account_id}")
            return profile
            
        except Exception as e:
            self.logger.error(f"사용자 프로필 조회 실패: {account_id}, 오류: {str(e)}")
            return None
    
    async def _save_token(
        self,
        account_id: UUID,
        token_response: Dict,
        scope: str,
    ) -> Token:
        """
        토큰 응답을 암호화하여 저장합니다.
        
        Args:
            account_id: 계정 ID
            token_response: Graph API 토큰 응답
            scope: 권한 범위
            
        Returns:
            저장된 토큰 엔티티
        """
        # 토큰 암호화
        encrypted_access_token = await self.encryption_service.encrypt(
            token_response['access_token']
        )
        
        encrypted_refresh_token = None
        if token_response.get('refresh_token'):
            encrypted_refresh_token = await self.encryption_service.encrypt(
                token_response['refresh_token']
            )
        
        # 만료 시간 계산 (서울 시간)
        from ..domain.entities import now_kst
        expires_in = token_response.get('expires_in', 3600)
        expires_at = now_kst() + timedelta(seconds=expires_in)
        
        # 토큰 엔티티 생성
        token = Token(
            account_id=account_id,
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            token_type=token_response.get('token_type', 'Bearer'),
            expires_at=expires_at,
            scope=scope,
        )
        
        # 토큰 저장
        return await self.token_repository.save(token)
    
    async def check_and_refresh_expiring_tokens(self, minutes: int = 5) -> int:
        """
        곧 만료될 토큰들을 확인하고 갱신합니다.
        
        Args:
            minutes: 만료 임박 기준 시간 (분)
            
        Returns:
            갱신된 토큰 개수
        """
        self.logger.info(f"만료 임박 토큰 확인 및 갱신 시작 (기준: {minutes}분)")
        
        # 곧 만료될 토큰 목록 조회
        expiring_tokens = await self.token_repository.list_near_expiry_tokens(minutes)
        
        refreshed_count = 0
        for token in expiring_tokens:
            try:
                refreshed_token = await self.refresh_token(token.account_id)
                if refreshed_token:
                    refreshed_count += 1
                    self.logger.info(f"토큰 자동 갱신 성공: {token.account_id}")
                else:
                    self.logger.warning(f"토큰 자동 갱신 실패: {token.account_id}")
            except Exception as e:
                self.logger.error(f"토큰 자동 갱신 오류: {token.account_id}, {str(e)}")
        
        self.logger.info(f"만료 임박 토큰 갱신 완료: {refreshed_count}/{len(expiring_tokens)}")
        return refreshed_count
    
    async def get_token_status(self, account_id: UUID) -> Optional[Dict]:
        """
        토큰 상태를 상세히 조회합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            토큰 상태 정보 딕셔너리 또는 None
        """
        self.logger.debug(f"토큰 상태 조회: {account_id}")
        
        # 토큰 조회
        token = await self.token_repository.get_by_account_id(account_id)
        if not token:
            return None
        
        try:
            # 기본 토큰 정보
            status = {
                "account_id": str(token.account_id),
                "token_type": token.token_type,
                "scope": token.scope,
                "created_at": token.created_at.isoformat(),
                "updated_at": token.updated_at.isoformat(),
                "db_expires_at": token.expires_at.isoformat(),
                "is_encrypted": token.is_encrypted(),
                "can_refresh": token.can_refresh(),
                "db_is_expired": token.is_expired(),
                "db_is_near_expiry": token.is_near_expiry(),
            }
            
            # 암호화된 토큰인 경우 복호화하여 JWT 정보 추출
            if token.is_encrypted():
                try:
                    decrypted_token = await self.encryption_service.decrypt(token.access_token)
                    status["is_jwt"] = token.is_jwt_token(decrypted_token)
                    
                    if status["is_jwt"]:
                        jwt_expiry = token.extract_jwt_expiry(decrypted_token)
                        if jwt_expiry:
                            status["jwt_expires_at"] = jwt_expiry.isoformat()
                            status["jwt_is_expired"] = token.is_expired_by_jwt(decrypted_token)
                            
                            # JWT와 DB 만료 시간 비교
                            time_diff = abs((jwt_expiry - token.expires_at).total_seconds())
                            status["expiry_time_diff_seconds"] = time_diff
                            status["expiry_times_match"] = time_diff < 60  # 1분 이내 차이면 일치로 간주
                        
                        # JWT 페이로드 정보 추출
                        try:
                            import json
                            import base64
                            
                            parts = decrypted_token.split('.')
                            if len(parts) == 3:
                                payload = parts[1]
                                payload += '=' * (4 - len(payload) % 4)
                                decoded_bytes = base64.urlsafe_b64decode(payload)
                                payload_data = json.loads(decoded_bytes.decode('utf-8'))
                                
                                status["jwt_payload"] = {
                                    "iss": payload_data.get("iss"),
                                    "aud": payload_data.get("aud"),
                                    "sub": payload_data.get("sub"),
                                    "appid": payload_data.get("appid"),
                                    "tid": payload_data.get("tid"),
                                    "upn": payload_data.get("upn"),
                                    "name": payload_data.get("name"),
                                    "scp": payload_data.get("scp"),
                                }
                        except Exception as e:
                            self.logger.warning(f"JWT 페이로드 파싱 실패: {str(e)}")
                            
                except Exception as e:
                    self.logger.error(f"토큰 복호화 실패: {str(e)}")
                    status["decryption_error"] = str(e)
            else:
                # 암호화되지 않은 토큰
                status["is_jwt"] = token.is_jwt_token()
            
            return status
            
        except Exception as e:
            self.logger.error(f"토큰 상태 조회 실패: {account_id}, 오류: {str(e)}")
            return None
    
    async def validate_token_integrity(self, account_id: UUID) -> Dict[str, bool]:
        """
        토큰의 무결성을 검증합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            검증 결과 딕셔너리
        """
        self.logger.debug(f"토큰 무결성 검증: {account_id}")
        
        result = {
            "token_exists": False,
            "is_encrypted": False,
            "decryption_success": False,
            "is_valid_jwt": False,
            "expiry_times_consistent": False,
            "token_not_expired": False,
            "overall_valid": False,
        }
        
        # 토큰 조회
        token = await self.token_repository.get_by_account_id(account_id)
        if not token:
            return result
        
        result["token_exists"] = True
        result["is_encrypted"] = token.is_encrypted()
        
        try:
            if token.is_encrypted():
                # 복호화 시도
                decrypted_token = await self.encryption_service.decrypt(token.access_token)
                result["decryption_success"] = True
                
                # JWT 유효성 검증
                if token.is_jwt_token(decrypted_token):
                    result["is_valid_jwt"] = True
                    
                    # 만료 시간 일관성 검증
                    jwt_expiry = token.extract_jwt_expiry(decrypted_token)
                    if jwt_expiry:
                        time_diff = abs((jwt_expiry - token.expires_at).total_seconds())
                        result["expiry_times_consistent"] = time_diff < 300  # 5분 이내 차이 허용
                        
                        # JWT 기준 만료 여부 확인
                        result["token_not_expired"] = not token.is_expired_by_jwt(decrypted_token)
                    else:
                        # JWT 만료 시간 추출 실패 시 DB 기준 사용
                        result["token_not_expired"] = not token.is_expired()
                else:
                    # JWT가 아닌 경우 DB 기준 사용
                    result["token_not_expired"] = not token.is_expired()
                    result["expiry_times_consistent"] = True  # JWT가 아니므로 일관성 문제 없음
            else:
                # 암호화되지 않은 토큰
                result["decryption_success"] = True
                result["is_valid_jwt"] = token.is_jwt_token()
                result["token_not_expired"] = not token.is_expired()
                result["expiry_times_consistent"] = True
            
            # 전체 유효성 판단
            result["overall_valid"] = (
                result["token_exists"] and
                result["decryption_success"] and
                result["expiry_times_consistent"] and
                result["token_not_expired"]
            )
            
        except Exception as e:
            self.logger.error(f"토큰 무결성 검증 실패: {account_id}, 오류: {str(e)}")
        
        return result
    
    async def log_raw_token_values(self, account_id: UUID) -> Dict[str, str]:
        """
        토큰의 원본 값들을 로그로 출력합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            토큰 원본 값들이 포함된 딕셔너리
        """
        self.logger.info(f"토큰 원본 값 로그 출력 시작: {account_id}")
        
        # 토큰 조회
        token = await self.token_repository.get_by_account_id(account_id)
        if not token:
            self.logger.warning(f"토큰을 찾을 수 없음: {account_id}")
            return {"error": "토큰을 찾을 수 없습니다"}
        
        result = {
            "account_id": str(account_id),
            "token_type": token.token_type,
            "scope": token.scope,
            "created_at": token.created_at.isoformat(),
            "expires_at": token.expires_at.isoformat(),
        }
        
        try:
            # 암호화된 액세스 토큰 복호화
            if token.is_encrypted():
                decrypted_access_token = await self.encryption_service.decrypt(token.access_token)
                result["encrypted_access_token"] = token.access_token
                result["decrypted_access_token"] = decrypted_access_token
                
                self.logger.info(f"[토큰 원본] 계정 ID: {account_id}")
                self.logger.info(f"[토큰 원본] 암호화된 액세스 토큰: {token.access_token}")
                self.logger.info(f"[토큰 원본] 복호화된 액세스 토큰: {decrypted_access_token}")
                
                # 리프레시 토큰이 있는 경우
                if token.refresh_token:
                    decrypted_refresh_token = await self.encryption_service.decrypt(token.refresh_token)
                    result["encrypted_refresh_token"] = token.refresh_token
                    result["decrypted_refresh_token"] = decrypted_refresh_token
                    
                    self.logger.info(f"[토큰 원본] 암호화된 리프레시 토큰: {token.refresh_token}")
                    self.logger.info(f"[토큰 원본] 복호화된 리프레시 토큰: {decrypted_refresh_token}")
                
                # JWT 토큰인 경우 페이로드 정보도 출력
                if token.is_jwt_token(decrypted_access_token):
                    self.logger.info(f"[토큰 원본] JWT 토큰 확인됨")
                    
                    try:
                        import json
                        import base64
                        
                        parts = decrypted_access_token.split('.')
                        if len(parts) == 3:
                            # Header 디코딩
                            header = parts[0]
                            header += '=' * (4 - len(header) % 4)
                            header_data = json.loads(base64.urlsafe_b64decode(header).decode('utf-8'))
                            
                            # Payload 디코딩
                            payload = parts[1]
                            payload += '=' * (4 - len(payload) % 4)
                            payload_data = json.loads(base64.urlsafe_b64decode(payload).decode('utf-8'))
                            
                            result["jwt_header"] = header_data
                            result["jwt_payload"] = payload_data
                            
                            self.logger.info(f"[토큰 원본] JWT Header: {json.dumps(header_data, indent=2)}")
                            self.logger.info(f"[토큰 원본] JWT Payload: {json.dumps(payload_data, indent=2)}")
                            
                            # 만료 시간 비교 - Token 클래스의 메서드 사용
                            jwt_expiry = token.extract_jwt_expiry(decrypted_access_token)
                            if jwt_expiry:
                                self.logger.info(f"[토큰 원본] JWT 만료 시간: {jwt_expiry.isoformat()}")
                                self.logger.info(f"[토큰 원본] DB 만료 시간: {token.expires_at.isoformat()}")
                                
                                time_diff = abs((jwt_expiry - token.expires_at).total_seconds())
                                self.logger.info(f"[토큰 원본] 만료 시간 차이: {time_diff}초")
                    
                    except Exception as e:
                        self.logger.error(f"JWT 파싱 실패: {str(e)}")
                        result["jwt_parse_error"] = str(e)
            else:
                # 암호화되지 않은 토큰
                result["access_token"] = token.access_token
                self.logger.info(f"[토큰 원본] 계정 ID: {account_id}")
                self.logger.info(f"[토큰 원본] 액세스 토큰 (암호화되지 않음): {token.access_token}")
                
                if token.refresh_token:
                    result["refresh_token"] = token.refresh_token
                    self.logger.info(f"[토큰 원본] 리프레시 토큰 (암호화되지 않음): {token.refresh_token}")
            
            # 토큰 상태 정보
            self.logger.info(f"[토큰 원본] 토큰 타입: {token.token_type}")
            self.logger.info(f"[토큰 원본] 권한 범위: {token.scope}")
            self.logger.info(f"[토큰 원본] 생성 시간: {token.created_at.isoformat()}")
            self.logger.info(f"[토큰 원본] 만료 시간: {token.expires_at.isoformat()}")
            self.logger.info(f"[토큰 원본] 만료 여부: {token.is_expired()}")
            self.logger.info(f"[토큰 원본] 갱신 가능 여부: {token.can_refresh()}")
            
        except Exception as e:
            error_msg = f"토큰 복호화 실패: {str(e)}"
            self.logger.error(f"[토큰 원본] {error_msg}")
            result["error"] = error_msg
        
        self.logger.info(f"토큰 원본 값 로그 출력 완료: {account_id}")
        return result
