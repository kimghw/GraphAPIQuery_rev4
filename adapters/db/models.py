"""
SQLAlchemy 데이터베이스 모델

도메인 엔티티와 매핑되는 데이터베이스 테이블 모델을 정의합니다.
SQLite 호환성을 위해 UUID는 String으로, ARRAY는 JSON으로 처리합니다.
성능 최적화를 위한 인덱스가 추가되었습니다.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.domain.entities import AccountStatus, AuthType, SyncStatus

# 서울 시간대 정의
KST = timezone(timedelta(hours=9))

def now_kst() -> datetime:
    """현재 서울 시간을 반환합니다."""
    return datetime.now(KST).replace(tzinfo=None)

Base = declarative_base()


class AccountModel(Base):
    """계정 테이블 모델"""
    
    __tablename__ = "accounts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255))
    auth_type = Column(String(50), nullable=False, index=True)  # AuthType enum을 문자열로 저장
    status = Column(String(50), nullable=False, default="inactive", index=True)  # AccountStatus enum을 문자열로 저장
    last_sync_at = Column(DateTime, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), index=True)
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_accounts_status_auth_type', 'status', 'auth_type'),
        Index('idx_accounts_email_status', 'email', 'status'),
        Index('idx_accounts_created_status', 'created_at', 'status'),
        Index('idx_accounts_last_sync_status', 'last_sync_at', 'status'),
    )
    
    # 관계 설정
    auth_code_config = relationship("AuthCodeConfigModel", back_populates="account", uselist=False)
    device_code_config = relationship("DeviceCodeConfigModel", back_populates="account", uselist=False)
    tokens = relationship("TokenModel", back_populates="account")
    mails = relationship("MailModel", back_populates="account")
    sync_histories = relationship("SyncHistoryModel", back_populates="account")
    delta_links = relationship("DeltaLinkModel", back_populates="account")
    webhook_subscriptions = relationship("WebhookSubscriptionModel", back_populates="account")


class AuthCodeConfigModel(Base):
    """Authorization Code Flow 설정 테이블 모델"""
    
    __tablename__ = "auth_code_configs"
    
    account_id = Column(String(36), ForeignKey("accounts.id"), primary_key=True)
    client_id = Column(String(255), nullable=False, index=True)
    client_secret = Column(Text, nullable=False)  # 암호화된 값
    redirect_uri = Column(String(500), nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_auth_code_client_tenant', 'client_id', 'tenant_id'),
    )
    
    # 관계 설정
    account = relationship("AccountModel", back_populates="auth_code_config")


class DeviceCodeConfigModel(Base):
    """Device Code Flow 설정 테이블 모델"""
    
    __tablename__ = "device_code_configs"
    
    account_id = Column(String(36), ForeignKey("accounts.id"), primary_key=True)
    client_id = Column(String(255), nullable=False, index=True)
    client_secret = Column(Text)  # 암호화된 값 (선택적)
    tenant_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_device_code_client_tenant', 'client_id', 'tenant_id'),
    )
    
    # 관계 설정
    account = relationship("AccountModel", back_populates="device_code_config")


class TokenModel(Base):
    """토큰 테이블 모델"""
    
    __tablename__ = "tokens"
    
    account_id = Column(String(36), ForeignKey("accounts.id"), primary_key=True)
    access_token = Column(Text, nullable=False)  # 암호화된 값
    refresh_token = Column(Text)  # 암호화된 값
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(DateTime, nullable=False, index=True)
    scope = Column(Text)
    created_at = Column(DateTime, default=now_kst, index=True)
    updated_at = Column(DateTime, default=now_kst, onupdate=now_kst)
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_tokens_account_expires', 'account_id', 'expires_at'),
        Index('idx_tokens_expires_created', 'expires_at', 'created_at'),
    )
    
    # 관계 설정
    account = relationship("AccountModel", back_populates="tokens")


class MailModel(Base):
    """메일 테이블 모델"""
    
    __tablename__ = "mails"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    message_id = Column(String(255), nullable=False, index=True)
    subject = Column(Text)
    sender = Column(String(255), index=True)
    recipients = Column(JSON)  # 문자열 배열을 JSON으로 저장
    cc_recipients = Column(JSON)  # 문자열 배열을 JSON으로 저장
    bcc_recipients = Column(JSON)  # 문자열 배열을 JSON으로 저장
    body_preview = Column(Text)
    body_content = Column(Text)
    body_content_type = Column(String(50))
    importance = Column(String(50), index=True)
    is_read = Column(Boolean, default=False, index=True)
    has_attachments = Column(Boolean, default=False, index=True)
    received_at = Column(DateTime, index=True)
    sent_at = Column(DateTime, index=True)
    processed_at = Column(DateTime, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_mails_account_received', 'account_id', 'received_at'),
        Index('idx_mails_account_processed', 'account_id', 'processed_at'),
        Index('idx_mails_account_read', 'account_id', 'is_read'),
        Index('idx_mails_sender_received', 'sender', 'received_at'),
        Index('idx_mails_message_account', 'message_id', 'account_id'),
        Index('idx_mails_received_read', 'received_at', 'is_read'),
        Index('idx_mails_importance_received', 'importance', 'received_at'),
        Index('idx_mails_attachments_received', 'has_attachments', 'received_at'),
    )
    
    # 관계 설정
    account = relationship("AccountModel", back_populates="mails")


class SyncHistoryModel(Base):
    """동기화 이력 테이블 모델"""
    
    __tablename__ = "sync_histories"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    sync_type = Column(String(50), nullable=False, index=True)  # 'full' or 'delta'
    status = Column(String(50), nullable=False, default="processing", index=True)  # SyncStatus enum을 문자열로 저장
    processed_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime, server_default=func.now(), index=True)
    completed_at = Column(DateTime, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_sync_account_started', 'account_id', 'started_at'),
        Index('idx_sync_account_status', 'account_id', 'status'),
        Index('idx_sync_type_status', 'sync_type', 'status'),
        Index('idx_sync_started_status', 'started_at', 'status'),
        Index('idx_sync_completed_status', 'completed_at', 'status'),
    )
    
    # 관계 설정
    account = relationship("AccountModel", back_populates="sync_histories")


class DeltaLinkModel(Base):
    """델타 링크 테이블 모델"""
    
    __tablename__ = "delta_links"
    
    account_id = Column(String(36), ForeignKey("accounts.id"), primary_key=True)
    delta_link = Column(Text, nullable=False)
    last_sync_at = Column(DateTime, server_default=func.now(), index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    account = relationship("AccountModel", back_populates="delta_links")


class WebhookSubscriptionModel(Base):
    """웹훅 구독 테이블 모델"""
    
    __tablename__ = "webhook_subscriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    subscription_id = Column(String(255), unique=True, nullable=False, index=True)
    resource = Column(String(255), nullable=False, index=True)
    change_types = Column(JSON, nullable=False)  # 문자열 배열을 JSON으로 저장
    notification_url = Column(String(500), nullable=False)
    client_state = Column(String(255))
    expires_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_webhook_account_active', 'account_id', 'is_active'),
        Index('idx_webhook_expires_active', 'expires_at', 'is_active'),
        Index('idx_webhook_resource_active', 'resource', 'is_active'),
        Index('idx_webhook_subscription_active', 'subscription_id', 'is_active'),
    )
    
    # 관계 설정
    account = relationship("AccountModel", back_populates="webhook_subscriptions")


class CacheModel(Base):
    """캐시 테이블 모델"""
    
    __tablename__ = "cache"
    
    key = Column(String(255), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_cache_key_expires', 'key', 'expires_at'),
    )
