"""
어댑터 팩토리

모든 어댑터들을 생성하고 의존성을 주입하는 팩토리 클래스입니다.
클린 아키텍처의 의존성 역전 원칙을 구현합니다.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.ports import (
    AccountRepositoryPort,
    AuthConfigRepositoryPort,
    TokenRepositoryPort,
    GraphApiClientPort,
    EncryptionServicePort,
    CacheServicePort,
    LoggerPort,
    ConfigPort,
)
from core.usecases.account_management import AccountManagementUseCase
from core.usecases.authentication import AuthenticationUseCase

from .db.repositories import (
    AccountRepositoryAdapter,
    AuthConfigRepositoryAdapter,
    TokenRepositoryAdapter,
)
from .external.graph_api_client import GraphApiClientAdapter
from .external.encryption_service import EncryptionServiceAdapter
from .external.cache_service import CacheServiceAdapter, InMemoryCacheServiceAdapter
from .logger import LoggerAdapter
from config.adapters import get_config


class AdapterFactory:
    """어댑터 팩토리"""
    
    def __init__(self, config: Optional[ConfigPort] = None):
        self.config = config or get_config()
        self._logger: Optional[LoggerPort] = None
        self._encryption_service: Optional[EncryptionServicePort] = None
        self._cache_service: Optional[CacheServicePort] = None
        self._graph_api_client: Optional[GraphApiClientPort] = None
    
    def create_logger(self) -> LoggerPort:
        """로거 어댑터를 생성합니다."""
        if self._logger is None:
            self._logger = LoggerAdapter(
                name="GraphAPIQuery",
                level=self.config.get_log_level(),
                format_string=self.config.get_log_format(),
            )
        return self._logger
    
    def create_encryption_service(self) -> EncryptionServicePort:
        """암호화 서비스 어댑터를 생성합니다."""
        if self._encryption_service is None:
            logger = self.create_logger()
            self._encryption_service = EncryptionServiceAdapter(
                encryption_key=self.config.get_encryption_key(),
                logger=logger,
            )
        return self._encryption_service
    
    def create_cache_service(self) -> CacheServicePort:
        """캐시 서비스 어댑터를 생성합니다."""
        if self._cache_service is None:
            logger = self.create_logger()
            
            # Redis URL이 설정되어 있으면 Redis 사용, 아니면 메모리 캐시 사용
            redis_url = self.config.get_redis_url()
            if redis_url and not redis_url.startswith("redis://localhost"):
                self._cache_service = CacheServiceAdapter(
                    redis_url=redis_url,
                    logger=logger,
                )
            else:
                # 개발/테스트 환경에서는 메모리 캐시 사용
                logger.info("Redis 설정이 없어 메모리 캐시를 사용합니다")
                self._cache_service = InMemoryCacheServiceAdapter(logger=logger)
        
        return self._cache_service
    
    def create_graph_api_client(self) -> GraphApiClientPort:
        """Graph API 클라이언트 어댑터를 생성합니다."""
        if self._graph_api_client is None:
            logger = self.create_logger()
            self._graph_api_client = GraphApiClientAdapter(logger=logger)
        return self._graph_api_client
    
    def create_account_repository(self, session: AsyncSession) -> AccountRepositoryPort:
        """계정 Repository 어댑터를 생성합니다."""
        return AccountRepositoryAdapter(session)
    
    def create_auth_config_repository(self, session: AsyncSession) -> AuthConfigRepositoryPort:
        """인증 설정 Repository 어댑터를 생성합니다."""
        return AuthConfigRepositoryAdapter(session)
    
    def create_token_repository(self, session: AsyncSession) -> TokenRepositoryPort:
        """토큰 Repository 어댑터를 생성합니다."""
        return TokenRepositoryAdapter(session)
    
    def create_account_management_usecase(self, session: AsyncSession) -> AccountManagementUseCase:
        """계정 관리 유즈케이스를 생성합니다."""
        account_repository = self.create_account_repository(session)
        auth_config_repository = self.create_auth_config_repository(session)
        logger = self.create_logger()
        
        return AccountManagementUseCase(
            account_repository=account_repository,
            auth_config_repository=auth_config_repository,
            logger=logger,
        )
    
    def create_authentication_usecase(self, session: AsyncSession) -> AuthenticationUseCase:
        """인증 유즈케이스를 생성합니다."""
        account_repository = self.create_account_repository(session)
        auth_config_repository = self.create_auth_config_repository(session)
        token_repository = self.create_token_repository(session)
        graph_api_client = self.create_graph_api_client()
        encryption_service = self.create_encryption_service()
        cache_service = self.create_cache_service()
        logger = self.create_logger()
        
        return AuthenticationUseCase(
            account_repository=account_repository,
            auth_config_repository=auth_config_repository,
            token_repository=token_repository,
            graph_api_client=graph_api_client,
            encryption_service=encryption_service,
            cache_service=cache_service,
            logger=logger,
        )
    
    def get_config(self) -> ConfigPort:
        """설정 객체를 반환합니다."""
        return self.config


# 전역 팩토리 인스턴스
_factory: Optional[AdapterFactory] = None


def get_adapter_factory() -> AdapterFactory:
    """전역 어댑터 팩토리 인스턴스를 반환합니다."""
    global _factory
    if _factory is None:
        _factory = AdapterFactory()
    return _factory


def initialize_adapter_factory(config: Optional[ConfigPort] = None) -> AdapterFactory:
    """어댑터 팩토리를 초기화합니다."""
    global _factory
    _factory = AdapterFactory(config)
    return _factory
