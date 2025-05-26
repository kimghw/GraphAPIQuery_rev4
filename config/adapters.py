"""
설정 어댑터

Core 레이어의 ConfigPort를 구현하는 Pydantic 기반 설정 어댑터입니다.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field, validator

from core.domain.ports import ConfigPort


class BaseConfig(BaseSettings, ConfigPort):
    """기본 설정 클래스"""
    
    # 환경 설정
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 데이터베이스 설정
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Redis 설정
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Microsoft Graph API 설정
    azure_client_id: str = Field(..., env="AZURE_CLIENT_ID")
    azure_client_secret: str = Field(..., env="AZURE_CLIENT_SECRET")
    azure_tenant_id: str = Field(..., env="AZURE_TENANT_ID")
    
    # OAuth 설정
    oauth_redirect_uri: str = Field(
        default="http://localhost:8080/auth/callback",
        env="OAUTH_REDIRECT_URI"
    )
    oauth_state_secret: str = Field(..., env="OAUTH_STATE_SECRET")
    
    # 암호화 설정
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    
    # JWT 설정
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    
    # 웹훅 설정
    webhook_secret: str = Field(..., env="WEBHOOK_SECRET")
    webhook_base_url: str = Field(
        default="http://localhost:8000",
        env="WEBHOOK_BASE_URL"
    )
    
    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # API 설정
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    
    # 메일 동기화 설정
    sync_batch_size: int = Field(default=100, env="SYNC_BATCH_SIZE")
    sync_interval_minutes: int = Field(default=5, env="SYNC_INTERVAL_MINUTES")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("encryption_key")
    def validate_encryption_key(cls, v):
        """암호화 키 검증"""
        if len(v) != 32:
            raise ValueError("암호화 키는 32바이트여야 합니다")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """로그 레벨 검증"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"로그 레벨은 {valid_levels} 중 하나여야 합니다")
        return v.upper()
    
    # ConfigPort 인터페이스 구현
    def get_environment(self) -> str:
        return self.environment
    
    def is_debug(self) -> bool:
        return self.debug
    
    def get_database_url(self) -> str:
        return self.database_url
    
    def get_redis_url(self) -> str:
        return self.redis_url
    
    def get_azure_client_id(self) -> str:
        return self.azure_client_id
    
    def get_azure_client_secret(self) -> str:
        return self.azure_client_secret
    
    def get_azure_tenant_id(self) -> str:
        return self.azure_tenant_id
    
    def get_oauth_redirect_uri(self) -> str:
        return self.oauth_redirect_uri
    
    def get_oauth_state_secret(self) -> str:
        return self.oauth_state_secret
    
    def get_encryption_key(self) -> str:
        return self.encryption_key
    
    def get_jwt_secret_key(self) -> str:
        return self.jwt_secret_key
    
    def get_jwt_algorithm(self) -> str:
        return self.jwt_algorithm
    
    def get_jwt_expire_minutes(self) -> int:
        return self.jwt_expire_minutes
    
    def get_webhook_secret(self) -> str:
        return self.webhook_secret
    
    def get_webhook_base_url(self) -> str:
        return self.webhook_base_url
    
    def get_log_level(self) -> str:
        return self.log_level
    
    def get_log_format(self) -> str:
        return self.log_format
    
    def get_api_host(self) -> str:
        return self.api_host
    
    def get_api_port(self) -> int:
        return self.api_port
    
    def get_api_workers(self) -> int:
        return self.api_workers
    
    def get_sync_batch_size(self) -> int:
        return self.sync_batch_size
    
    def get_sync_interval_minutes(self) -> int:
        return self.sync_interval_minutes
    
    def get_azure_config(self) -> dict:
        """Azure 설정 조회"""
        return {
            "client_id": self.azure_client_id,
            "client_secret": self.azure_client_secret,
            "tenant_id": self.azure_tenant_id,
        }
    
    def get_api_config(self) -> dict:
        """API 설정 조회"""
        return {
            "host": self.api_host,
            "port": self.api_port,
            "workers": self.api_workers,
        }
    
    def get_log_config(self) -> dict:
        """로그 설정 조회"""
        return {
            "level": self.log_level,
            "format": self.log_format,
        }


class DevelopmentConfig(BaseConfig):
    """개발 환경 설정"""
    
    environment: str = "development"
    debug: bool = True
    log_level: str = "DEBUG"
    
    # 개발용 기본값들
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/graphapi_dev",
        env="DATABASE_URL"
    )
    
    # 개발용 더미 값들 (실제 사용 시 .env 파일에서 설정)
    azure_client_id: str = Field(default="dev_client_id", env="AZURE_CLIENT_ID")
    azure_client_secret: str = Field(default="dev_client_secret", env="AZURE_CLIENT_SECRET")
    azure_tenant_id: str = Field(default="dev_tenant_id", env="AZURE_TENANT_ID")
    oauth_state_secret: str = Field(default="dev_oauth_state_secret_32_bytes", env="OAUTH_STATE_SECRET")
    encryption_key: str = Field(default="dev_encryption_key_32_bytes_long", env="ENCRYPTION_KEY")
    jwt_secret_key: str = Field(default="dev_jwt_secret_key", env="JWT_SECRET_KEY")
    webhook_secret: str = Field(default="dev_webhook_secret", env="WEBHOOK_SECRET")


class ProductionConfig(BaseConfig):
    """운영 환경 설정"""
    
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    
    @validator("database_url")
    def validate_production_database_url(cls, v):
        """운영 환경에서는 데이터베이스 URL이 필수"""
        if not v or v.startswith("sqlite"):
            raise ValueError("운영 환경에서는 PostgreSQL 데이터베이스가 필요합니다")
        return v
    
    @validator("azure_client_secret", "oauth_state_secret", "encryption_key", "jwt_secret_key", "webhook_secret")
    def validate_production_secrets(cls, v):
        """운영 환경에서는 모든 시크릿이 필수"""
        if not v:
            raise ValueError("운영 환경에서는 모든 시크릿 값이 필요합니다")
        return v


class TestingConfig(BaseConfig):
    """테스트 환경 설정"""
    
    environment: str = "testing"
    debug: bool = True
    log_level: str = "WARNING"
    
    # 테스트용 기본값들
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/graphapi_test",
        env="DATABASE_URL"
    )
    
    # 테스트용 더미 값들
    azure_client_id: str = "test_client_id"
    azure_client_secret: str = "test_client_secret"
    azure_tenant_id: str = "test_tenant_id"
    oauth_state_secret: str = "test_oauth_state_secret_32_bytes"
    encryption_key: str = "test_encryption_key_32_bytes_long"
    jwt_secret_key: str = "test_jwt_secret_key"
    webhook_secret: str = "test_webhook_secret"


class ConfigAdapter:
    """설정 어댑터 팩토리"""
    
    @staticmethod
    def create_config() -> ConfigPort:
        """환경에 따른 설정 객체를 생성합니다."""
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        if environment == "production":
            return ProductionConfig()
        elif environment == "testing":
            return TestingConfig()
        else:
            return DevelopmentConfig()


# 전역 설정 인스턴스
_config: Optional[ConfigPort] = None


def get_config() -> ConfigPort:
    """전역 설정 인스턴스를 반환합니다."""
    global _config
    if _config is None:
        _config = ConfigAdapter.create_config()
    return _config


def initialize_config() -> ConfigPort:
    """설정을 초기화합니다."""
    global _config
    _config = ConfigAdapter.create_config()
    return _config
