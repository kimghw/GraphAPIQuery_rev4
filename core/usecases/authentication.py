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
        scope: str = "https://graph.microsoft.com/.default",
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
        scope: str = "https://graph.microsoft.com/.default",
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
        scope: str = "https://graph.microsoft.com/.default",
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
        scope: str = "https://graph.microsoft.com/.default",
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
        
        # 만료 시간 계산
        expires_in = token_response.get('expires_in', 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
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
