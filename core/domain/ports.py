"""
포트 인터페이스 정의

클린 아키텍처의 핵심으로, Core 레이어와 외부 어댑터 간의 계약을 정의합니다.
모든 포트는 추상 기본 클래스(ABC)로 정의되어 구현을 강제합니다.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from .entities import (
    Account,
    AuthCodeConfig,
    DeviceCodeConfig,
    DeltaLink,
    Mail,
    SyncHistory,
    Token,
    WebhookSubscription,
)


class AccountRepositoryPort(ABC):
    """계정 저장소 포트"""
    
    @abstractmethod
    async def create(self, account: Account) -> Account:
        """계정 생성"""
        pass
    
    @abstractmethod
    async def get_by_id(self, account_id: UUID) -> Optional[Account]:
        """ID로 계정 조회"""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[Account]:
        """이메일로 계정 조회"""
        pass
    
    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Account]:
        """모든 계정 목록 조회"""
        pass
    
    @abstractmethod
    async def list_active(self) -> List[Account]:
        """활성 계정 목록 조회"""
        pass
    
    @abstractmethod
    async def update(self, account: Account) -> Account:
        """계정 정보 업데이트"""
        pass
    
    @abstractmethod
    async def delete(self, account_id: UUID) -> bool:
        """계정 삭제"""
        pass
    
    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """이메일로 계정 존재 여부 확인"""
        pass


class AuthConfigRepositoryPort(ABC):
    """인증 설정 저장소 포트"""
    
    @abstractmethod
    async def create_auth_code_config(self, config: AuthCodeConfig) -> AuthCodeConfig:
        """Authorization Code 설정 생성"""
        pass
    
    @abstractmethod
    async def create_device_code_config(self, config: DeviceCodeConfig) -> DeviceCodeConfig:
        """Device Code 설정 생성"""
        pass
    
    @abstractmethod
    async def get_auth_code_config(self, account_id: UUID) -> Optional[AuthCodeConfig]:
        """Authorization Code 설정 조회"""
        pass
    
    @abstractmethod
    async def get_device_code_config(self, account_id: UUID) -> Optional[DeviceCodeConfig]:
        """Device Code 설정 조회"""
        pass
    
    @abstractmethod
    async def update_auth_code_config(self, config: AuthCodeConfig) -> AuthCodeConfig:
        """Authorization Code 설정 업데이트"""
        pass
    
    @abstractmethod
    async def delete_config(self, account_id: UUID) -> bool:
        """인증 설정 삭제"""
        pass


class TokenRepositoryPort(ABC):
    """토큰 저장소 포트"""
    
    @abstractmethod
    async def save(self, token: Token) -> Token:
        """토큰 저장"""
        pass
    
    @abstractmethod
    async def get_by_account_id(self, account_id: UUID) -> Optional[Token]:
        """계정 ID로 토큰 조회"""
        pass
    
    @abstractmethod
    async def update(self, token: Token) -> Token:
        """토큰 업데이트"""
        pass
    
    @abstractmethod
    async def delete(self, account_id: UUID) -> bool:
        """토큰 삭제"""
        pass
    
    @abstractmethod
    async def list_expired_tokens(self) -> List[Token]:
        """만료된 토큰 목록 조회"""
        pass
    
    @abstractmethod
    async def list_near_expiry_tokens(self, minutes: int = 5) -> List[Token]:
        """곧 만료될 토큰 목록 조회"""
        pass


class MailRepositoryPort(ABC):
    """메일 저장소 포트"""
    
    @abstractmethod
    async def create(self, mail: Mail) -> Mail:
        """메일 생성"""
        pass
    
    @abstractmethod
    async def get_by_id(self, mail_id: UUID) -> Optional[Mail]:
        """ID로 메일 조회"""
        pass
    
    @abstractmethod
    async def get_by_message_id(self, account_id: UUID, message_id: str) -> Optional[Mail]:
        """메시지 ID로 메일 조회"""
        pass
    
    @abstractmethod
    async def list_by_account(
        self,
        account_id: UUID,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Mail]:
        """계정별 메일 목록 조회"""
        pass
    
    @abstractmethod
    async def list_unprocessed(self, account_id: UUID) -> List[Mail]:
        """미처리 메일 목록 조회"""
        pass
    
    @abstractmethod
    async def update(self, mail: Mail) -> Mail:
        """메일 업데이트"""
        pass
    
    @abstractmethod
    async def delete(self, mail_id: UUID) -> bool:
        """메일 삭제"""
        pass
    
    @abstractmethod
    async def exists_by_message_id(self, account_id: UUID, message_id: str) -> bool:
        """메시지 ID로 메일 존재 여부 확인"""
        pass


class SyncHistoryRepositoryPort(ABC):
    """동기화 이력 저장소 포트"""
    
    @abstractmethod
    async def create(self, sync_history: SyncHistory) -> SyncHistory:
        """동기화 이력 생성"""
        pass
    
    @abstractmethod
    async def get_by_id(self, sync_id: UUID) -> Optional[SyncHistory]:
        """ID로 동기화 이력 조회"""
        pass
    
    @abstractmethod
    async def list_by_account(
        self,
        account_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SyncHistory]:
        """계정별 동기화 이력 조회"""
        pass
    
    @abstractmethod
    async def get_latest_by_account(self, account_id: UUID) -> Optional[SyncHistory]:
        """계정의 최신 동기화 이력 조회"""
        pass
    
    @abstractmethod
    async def update(self, sync_history: SyncHistory) -> SyncHistory:
        """동기화 이력 업데이트"""
        pass
    
    @abstractmethod
    async def delete(self, sync_id: UUID) -> bool:
        """동기화 이력 삭제"""
        pass


class DeltaLinkRepositoryPort(ABC):
    """델타 링크 저장소 포트"""
    
    @abstractmethod
    async def save(self, delta_link: DeltaLink) -> DeltaLink:
        """델타 링크 저장"""
        pass
    
    @abstractmethod
    async def get_by_account_id(self, account_id: UUID) -> Optional[DeltaLink]:
        """계정 ID로 델타 링크 조회"""
        pass
    
    @abstractmethod
    async def update(self, delta_link: DeltaLink) -> DeltaLink:
        """델타 링크 업데이트"""
        pass
    
    @abstractmethod
    async def delete(self, account_id: UUID) -> bool:
        """델타 링크 삭제"""
        pass


class WebhookSubscriptionRepositoryPort(ABC):
    """웹훅 구독 저장소 포트"""
    
    @abstractmethod
    async def create(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """웹훅 구독 생성"""
        pass
    
    @abstractmethod
    async def get_by_id(self, subscription_id: UUID) -> Optional[WebhookSubscription]:
        """ID로 웹훅 구독 조회"""
        pass
    
    @abstractmethod
    async def get_by_account_id(self, account_id: UUID) -> Optional[WebhookSubscription]:
        """계정 ID로 웹훅 구독 조회"""
        pass
    
    @abstractmethod
    async def list_expired(self) -> List[WebhookSubscription]:
        """만료된 웹훅 구독 목록 조회"""
        pass
    
    @abstractmethod
    async def list_near_expiry(self, hours: int = 24) -> List[WebhookSubscription]:
        """곧 만료될 웹훅 구독 목록 조회"""
        pass
    
    @abstractmethod
    async def update(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """웹훅 구독 업데이트"""
        pass
    
    @abstractmethod
    async def delete(self, subscription_id: UUID) -> bool:
        """웹훅 구독 삭제"""
        pass


class GraphApiClientPort(ABC):
    """Microsoft Graph API 클라이언트 포트"""
    
    @abstractmethod
    async def get_authorization_url(
        self,
        client_id: str,
        tenant_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
    ) -> str:
        """인증 URL 생성"""
        pass
    
    @abstractmethod
    async def get_device_code(
        self,
        client_id: str,
        tenant_id: str,
        scope: str,
    ) -> dict:
        """디바이스 코드 요청"""
        pass
    
    @abstractmethod
    async def exchange_code_for_token(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        redirect_uri: str,
        code: str,
    ) -> dict:
        """인증 코드를 토큰으로 교환"""
        pass
    
    @abstractmethod
    async def poll_device_code(
        self,
        client_id: str,
        tenant_id: str,
        device_code: str,
    ) -> dict:
        """디바이스 코드 폴링"""
        pass
    
    @abstractmethod
    async def refresh_token(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        refresh_token: str,
    ) -> dict:
        """토큰 갱신"""
        pass
    
    @abstractmethod
    async def get_user_profile(self, access_token: str) -> dict:
        """사용자 프로필 조회"""
        pass
    
    @abstractmethod
    async def list_messages(
        self,
        access_token: str,
        top: int = 50,
        skip: int = 0,
        filter_query: Optional[str] = None,
        order_by: Optional[str] = None,
    ) -> dict:
        """메시지 목록 조회"""
        pass
    
    @abstractmethod
    async def get_message(self, access_token: str, message_id: str) -> dict:
        """특정 메시지 조회"""
        pass
    
    @abstractmethod
    async def send_message(self, access_token: str, message_data: dict) -> dict:
        """메시지 발송"""
        pass
    
    @abstractmethod
    async def get_delta_messages(self, access_token: str, delta_link: str) -> dict:
        """델타 메시지 조회"""
        pass
    
    @abstractmethod
    async def create_subscription(
        self,
        access_token: str,
        resource: str,
        change_types: List[str],
        notification_url: str,
        expiration_datetime: str,
        client_state: Optional[str] = None,
    ) -> dict:
        """웹훅 구독 생성"""
        pass
    
    @abstractmethod
    async def update_subscription(
        self,
        access_token: str,
        subscription_id: str,
        expiration_datetime: str,
    ) -> dict:
        """웹훅 구독 업데이트"""
        pass
    
    @abstractmethod
    async def delete_subscription(
        self,
        access_token: str,
        subscription_id: str,
    ) -> bool:
        """웹훅 구독 삭제"""
        pass


class EncryptionServicePort(ABC):
    """암호화 서비스 포트"""
    
    @abstractmethod
    async def encrypt(self, data: str) -> str:
        """데이터 암호화"""
        pass
    
    @abstractmethod
    async def decrypt(self, encrypted_data: str) -> str:
        """데이터 복호화"""
        pass


class ExternalApiClientPort(ABC):
    """외부 API 클라이언트 포트"""
    
    @abstractmethod
    async def send_mail_data(self, mail_data: dict) -> bool:
        """메일 데이터를 외부 API로 전송"""
        pass
    
    @abstractmethod
    async def send_notification(self, notification_data: dict) -> bool:
        """알림을 외부 API로 전송"""
        pass


class CacheServicePort(ABC):
    """캐시 서비스 포트"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """캐시에서 값 조회"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """캐시에 키 존재 여부 확인"""
        pass


class LoggerPort(ABC):
    """로거 포트"""
    
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """정보 로그"""
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """경고 로그"""
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """오류 로그"""
        pass
    
    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """디버그 로그"""
        pass


class ConfigPort(ABC):
    """설정 포트"""
    
    # 환경 설정
    @abstractmethod
    def get_environment(self) -> str:
        """환경 조회 (development, production, testing)"""
        pass
    
    @abstractmethod
    def is_debug(self) -> bool:
        """디버그 모드 여부"""
        pass
    
    # 데이터베이스 설정
    @abstractmethod
    def get_database_url(self) -> str:
        """데이터베이스 URL 조회"""
        pass
    
    # 캐시 설정 (Redis 제거, 데이터베이스 기반으로 변경)
    @abstractmethod
    def get_cache_ttl(self) -> int:
        """캐시 기본 TTL (초) 조회"""
        pass
    
    # Microsoft Azure 설정
    @abstractmethod
    def get_azure_client_id(self) -> str:
        """Azure 클라이언트 ID 조회"""
        pass
    
    @abstractmethod
    def get_azure_client_secret(self) -> str:
        """Azure 클라이언트 시크릿 조회"""
        pass
    
    @abstractmethod
    def get_azure_tenant_id(self) -> str:
        """Azure 테넌트 ID 조회"""
        pass
    
    # OAuth 설정
    @abstractmethod
    def get_oauth_redirect_uri(self) -> str:
        """OAuth 리다이렉트 URI 조회"""
        pass
    
    @abstractmethod
    def get_oauth_state_secret(self) -> str:
        """OAuth State 시크릿 키 조회"""
        pass
    
    # 보안 설정
    @abstractmethod
    def get_encryption_key(self) -> str:
        """암호화 키 조회"""
        pass
    
    @abstractmethod
    def get_jwt_secret_key(self) -> str:
        """JWT 시크릿 키 조회"""
        pass
    
    @abstractmethod
    def get_jwt_algorithm(self) -> str:
        """JWT 알고리즘 조회"""
        pass
    
    @abstractmethod
    def get_jwt_expire_minutes(self) -> int:
        """JWT 만료 시간(분) 조회"""
        pass
    
    # 웹훅 설정
    @abstractmethod
    def get_webhook_secret(self) -> str:
        """웹훅 시크릿 조회"""
        pass
    
    @abstractmethod
    def get_webhook_base_url(self) -> str:
        """웹훅 베이스 URL 조회"""
        pass
    
    # 로깅 설정
    @abstractmethod
    def get_log_level(self) -> str:
        """로그 레벨 조회"""
        pass
    
    @abstractmethod
    def get_log_format(self) -> str:
        """로그 포맷 조회"""
        pass
    
    # 웹 서버 설정
    @abstractmethod
    def get_web_host(self) -> str:
        """웹 서버 호스트 조회"""
        pass
    
    @abstractmethod
    def get_web_port(self) -> int:
        """웹 서버 포트 조회"""
        pass
    
    @abstractmethod
    def get_web_workers(self) -> int:
        """웹 서버 워커 수 조회"""
        pass
    
    # API 서버 설정 (향후 REST API용)
    @abstractmethod
    def get_api_host(self) -> str:
        """API 서버 호스트 조회"""
        pass
    
    @abstractmethod
    def get_api_port(self) -> int:
        """API 서버 포트 조회"""
        pass
    
    @abstractmethod
    def get_api_workers(self) -> int:
        """API 서버 워커 수 조회"""
        pass
    
    # 동기화 설정
    @abstractmethod
    def get_sync_batch_size(self) -> int:
        """동기화 배치 크기 조회"""
        pass
    
    @abstractmethod
    def get_sync_interval_minutes(self) -> int:
        """동기화 간격(분) 조회"""
        pass
    
    # 복합 설정 조회 메서드
    @abstractmethod
    def get_azure_config(self) -> dict:
        """Azure 설정 조회"""
        pass
    
    @abstractmethod
    def get_web_config(self) -> dict:
        """웹 서버 설정 조회"""
        pass
    
    @abstractmethod
    def get_api_config(self) -> dict:
        """API 서버 설정 조회"""
        pass
    
    @abstractmethod
    def get_log_config(self) -> dict:
        """로그 설정 조회"""
        pass
