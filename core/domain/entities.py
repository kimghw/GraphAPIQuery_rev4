"""
도메인 엔티티 정의

비즈니스 핵심 개념을 나타내는 엔티티들을 정의합니다.
모든 엔티티는 Pydantic 모델을 기반으로 하여 타입 안정성을 보장합니다.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class AuthType(str, Enum):
    """인증 방식"""
    AUTHORIZATION_CODE = "authorization_code"
    DEVICE_CODE = "device_code"


class AccountStatus(str, Enum):
    """계정 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class SyncStatus(str, Enum):
    """동기화 상태"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    PROCESSING = "processing"


class TokenType(str, Enum):
    """토큰 타입"""
    ACCESS = "access"
    REFRESH = "refresh"


class Account(BaseModel):
    """Microsoft 365 계정 엔티티"""
    
    id: UUID = Field(default_factory=uuid4, description="계정 고유 ID")
    email: str = Field(..., description="계정 이메일 주소")
    display_name: Optional[str] = Field(None, description="표시 이름")
    auth_type: AuthType = Field(..., description="인증 방식")
    status: AccountStatus = Field(default=AccountStatus.INACTIVE, description="계정 상태")
    tenant_id: Optional[str] = Field(None, description="Azure AD 테넌트 ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성 시간")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="수정 시간")
    last_sync_at: Optional[datetime] = Field(None, description="마지막 동기화 시간")
    
    @validator('email')
    def validate_email(cls, v):
        """이메일 형식 검증"""
        if '@' not in v:
            raise ValueError('유효한 이메일 주소가 아닙니다')
        return v.lower()
    
    def is_active(self) -> bool:
        """계정이 활성 상태인지 확인"""
        return self.status == AccountStatus.ACTIVE
    
    def can_sync(self) -> bool:
        """동기화 가능한 상태인지 확인"""
        return self.status in [AccountStatus.ACTIVE]
    
    def activate(self) -> None:
        """계정 활성화"""
        self.status = AccountStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """계정 비활성화"""
        self.status = AccountStatus.INACTIVE
        self.updated_at = datetime.utcnow()
    
    def mark_error(self) -> None:
        """계정을 오류 상태로 표시"""
        self.status = AccountStatus.ERROR
        self.updated_at = datetime.utcnow()


class AuthConfig(BaseModel):
    """인증 설정 기본 클래스"""
    
    account_id: UUID = Field(..., description="계정 ID")
    client_id: str = Field(..., description="Azure 애플리케이션 클라이언트 ID")
    tenant_id: str = Field(..., description="Azure AD 테넌트 ID")


class AuthCodeConfig(AuthConfig):
    """Authorization Code Flow 설정"""
    
    client_secret: str = Field(..., description="클라이언트 시크릿")
    redirect_uri: str = Field(..., description="리다이렉트 URI")
    
    @validator('redirect_uri')
    def validate_redirect_uri(cls, v):
        """리다이렉트 URI 검증"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('유효한 URL이 아닙니다')
        return v


class DeviceCodeConfig(AuthConfig):
    """Device Code Flow 설정"""
    
    # Device Code Flow는 추가 설정이 필요하지 않음
    pass


class Token(BaseModel):
    """OAuth 토큰 엔티티"""
    
    account_id: UUID = Field(..., description="계정 ID")
    access_token: str = Field(..., description="액세스 토큰")
    refresh_token: Optional[str] = Field(None, description="리프레시 토큰")
    token_type: str = Field(default="Bearer", description="토큰 타입")
    expires_at: datetime = Field(..., description="만료 시간")
    scope: str = Field(..., description="권한 범위")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성 시간")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="수정 시간")
    
    def is_expired(self) -> bool:
        """토큰이 만료되었는지 확인"""
        return datetime.utcnow() >= self.expires_at
    
    def is_near_expiry(self, minutes: int = 5) -> bool:
        """토큰이 곧 만료될지 확인"""
        from datetime import timedelta
        return datetime.utcnow() + timedelta(minutes=minutes) >= self.expires_at
    
    def can_refresh(self) -> bool:
        """토큰 갱신 가능한지 확인"""
        return self.refresh_token is not None


class Mail(BaseModel):
    """메일 메시지 엔티티"""
    
    id: UUID = Field(default_factory=uuid4, description="내부 메일 ID")
    account_id: UUID = Field(..., description="계정 ID")
    message_id: str = Field(..., description="Graph API 메시지 ID")
    subject: Optional[str] = Field(None, description="메일 제목")
    sender: Optional[str] = Field(None, description="발신자")
    recipients: List[str] = Field(default_factory=list, description="수신자 목록")
    cc_recipients: List[str] = Field(default_factory=list, description="참조 수신자 목록")
    bcc_recipients: List[str] = Field(default_factory=list, description="숨은참조 수신자 목록")
    body_preview: Optional[str] = Field(None, description="본문 미리보기")
    body_content: Optional[str] = Field(None, description="본문 내용")
    body_content_type: Optional[str] = Field(None, description="본문 콘텐츠 타입")
    importance: Optional[str] = Field(None, description="중요도")
    is_read: bool = Field(default=False, description="읽음 여부")
    has_attachments: bool = Field(default=False, description="첨부파일 여부")
    received_at: datetime = Field(..., description="수신 시간")
    sent_at: Optional[datetime] = Field(None, description="발송 시간")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성 시간")
    processed_at: Optional[datetime] = Field(None, description="처리 시간")
    
    def mark_as_processed(self) -> None:
        """메일을 처리됨으로 표시"""
        self.processed_at = datetime.utcnow()
    
    def is_processed(self) -> bool:
        """메일이 처리되었는지 확인"""
        return self.processed_at is not None


class SyncHistory(BaseModel):
    """동기화 이력 엔티티"""
    
    id: UUID = Field(default_factory=uuid4, description="동기화 이력 ID")
    account_id: UUID = Field(..., description="계정 ID")
    sync_type: str = Field(..., description="동기화 타입 (full/delta)")
    status: SyncStatus = Field(..., description="동기화 상태")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="시작 시간")
    completed_at: Optional[datetime] = Field(None, description="완료 시간")
    processed_count: int = Field(default=0, description="처리된 메일 수")
    error_count: int = Field(default=0, description="오류 발생 수")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    
    def mark_as_completed(self) -> None:
        """동기화 완료로 표시"""
        self.status = SyncStatus.SUCCESS
        self.completed_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str) -> None:
        """동기화 실패로 표시"""
        self.status = SyncStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
    
    def is_completed(self) -> bool:
        """동기화가 완료되었는지 확인"""
        return self.status in [SyncStatus.SUCCESS, SyncStatus.FAILED]


class DeltaLink(BaseModel):
    """증분 동기화를 위한 델타 링크 엔티티"""
    
    account_id: UUID = Field(..., description="계정 ID")
    delta_link: str = Field(..., description="델타 링크 URL")
    last_sync_at: datetime = Field(default_factory=datetime.utcnow, description="마지막 동기화 시간")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성 시간")
    
    def update_link(self, new_delta_link: str) -> None:
        """델타 링크 업데이트"""
        self.delta_link = new_delta_link
        self.last_sync_at = datetime.utcnow()


class WebhookSubscription(BaseModel):
    """웹훅 구독 엔티티"""
    
    id: UUID = Field(default_factory=uuid4, description="구독 ID")
    account_id: UUID = Field(..., description="계정 ID")
    subscription_id: str = Field(..., description="Graph API 구독 ID")
    resource: str = Field(..., description="구독 리소스")
    change_types: List[str] = Field(..., description="변경 타입 목록")
    notification_url: str = Field(..., description="알림 URL")
    expires_at: datetime = Field(..., description="만료 시간")
    client_state: Optional[str] = Field(None, description="클라이언트 상태")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성 시간")
    
    def is_expired(self) -> bool:
        """구독이 만료되었는지 확인"""
        return datetime.utcnow() >= self.expires_at
    
    def is_near_expiry(self, hours: int = 24) -> bool:
        """구독이 곧 만료될지 확인"""
        from datetime import timedelta
        return datetime.utcnow() + timedelta(hours=hours) >= self.expires_at
