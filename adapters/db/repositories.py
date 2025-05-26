"""
데이터베이스 Repository 어댑터

Core 레이어의 Repository 포트를 구현하는 SQLAlchemy 기반 어댑터들입니다.
SQLite 호환성을 위해 UUID를 문자열로 변환하여 처리합니다.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from core.domain.entities import (
    Account,
    AccountStatus,
    AuthCodeConfig,
    AuthType,
    DeviceCodeConfig,
    Token,
)
from core.domain.ports import AccountRepositoryPort, AuthConfigRepositoryPort, TokenRepositoryPort
from .models import AccountModel, AuthCodeConfigModel, DeviceCodeConfigModel, TokenModel


class AccountRepositoryAdapter(AccountRepositoryPort):
    """계정 Repository 어댑터"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, account: Account) -> Account:
        """계정을 생성합니다."""
        model = AccountModel(
            id=str(account.id),  # UUID를 문자열로 변환
            email=account.email,
            display_name=account.display_name,
            auth_type=account.auth_type.value,  # Enum을 문자열로 변환
            status=account.status.value,  # Enum을 문자열로 변환
            last_sync_at=account.last_sync_at,
        )
        
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        
        return self._model_to_entity(model)
    
    async def get_by_id(self, account_id: UUID) -> Optional[Account]:
        """ID로 계정을 조회합니다."""
        stmt = select(AccountModel).where(AccountModel.id == str(account_id))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            return None
        
        return self._model_to_entity(model)
    
    async def get_by_email(self, email: str) -> Optional[Account]:
        """이메일로 계정을 조회합니다."""
        stmt = select(AccountModel).where(AccountModel.email == email)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            return None
        
        return self._model_to_entity(model)
    
    async def update(self, account: Account) -> Account:
        """계정을 업데이트합니다."""
        stmt = select(AccountModel).where(AccountModel.id == str(account.id))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            raise ValueError(f"계정을 찾을 수 없습니다: {account.id}")
        
        # 업데이트할 필드들
        model.email = account.email
        model.display_name = account.display_name
        model.auth_type = account.auth_type.value
        model.status = account.status.value
        model.last_sync_at = account.last_sync_at
        model.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(model)
        
        return self._model_to_entity(model)
    
    async def delete(self, account_id: UUID) -> bool:
        """계정을 삭제합니다."""
        stmt = select(AccountModel).where(AccountModel.id == str(account_id))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            return False
        
        await self.session.delete(model)
        await self.session.commit()
        
        return True
    
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Account]:
        """모든 계정을 조회합니다."""
        stmt = (
            select(AccountModel)
            .order_by(desc(AccountModel.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def list_active(self) -> List[Account]:
        """활성 계정 목록을 조회합니다."""
        stmt = (
            select(AccountModel)
            .where(AccountModel.status == AccountStatus.ACTIVE.value)
            .order_by(desc(AccountModel.created_at))
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def list_by_status(
        self,
        status: AccountStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Account]:
        """상태별로 계정을 조회합니다."""
        stmt = (
            select(AccountModel)
            .where(AccountModel.status == status.value)
            .order_by(desc(AccountModel.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def list_by_auth_type(
        self,
        auth_type: AuthType,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Account]:
        """인증 타입별로 계정을 조회합니다."""
        stmt = (
            select(AccountModel)
            .where(AccountModel.auth_type == auth_type.value)
            .order_by(desc(AccountModel.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def exists_by_email(self, email: str) -> bool:
        """이메일로 계정 존재 여부를 확인합니다."""
        stmt = select(AccountModel.id).where(AccountModel.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def count_by_status(self, status: AccountStatus) -> int:
        """상태별 계정 수를 조회합니다."""
        stmt = select(AccountModel).where(AccountModel.status == status.value)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return len(models)
    
    async def search_by_email_pattern(
        self,
        email_pattern: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Account]:
        """이메일 패턴으로 계정을 검색합니다."""
        stmt = (
            select(AccountModel)
            .where(AccountModel.email.ilike(f"%{email_pattern}%"))
            .order_by(desc(AccountModel.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _model_to_entity(self, model: AccountModel) -> Account:
        """모델을 엔티티로 변환합니다."""
        return Account(
            id=UUID(model.id),  # 문자열을 UUID로 변환
            email=model.email,
            display_name=model.display_name,
            auth_type=AuthType(model.auth_type),  # 문자열을 Enum으로 변환
            status=AccountStatus(model.status),  # 문자열을 Enum으로 변환
            last_sync_at=model.last_sync_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class AuthConfigRepositoryAdapter(AuthConfigRepositoryPort):
    """인증 설정 Repository 어댑터"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_auth_code_config(self, config: AuthCodeConfig) -> AuthCodeConfig:
        """Authorization Code 설정을 생성합니다."""
        return await self.save_auth_code_config(config)
    
    async def create_device_code_config(self, config: DeviceCodeConfig) -> DeviceCodeConfig:
        """Device Code 설정을 생성합니다."""
        return await self.save_device_code_config(config)
    
    async def update_auth_code_config(self, config: AuthCodeConfig) -> AuthCodeConfig:
        """Authorization Code 설정을 업데이트합니다."""
        return await self.save_auth_code_config(config)
    
    async def delete_config(self, account_id: UUID) -> bool:
        """인증 설정을 삭제합니다."""
        # Authorization Code 설정 삭제 시도
        auth_code_deleted = await self.delete_auth_code_config(account_id)
        # Device Code 설정 삭제 시도
        device_code_deleted = await self.delete_device_code_config(account_id)
        
        # 둘 중 하나라도 삭제되었으면 True 반환
        return auth_code_deleted or device_code_deleted
    
    async def save_auth_code_config(self, config: AuthCodeConfig) -> AuthCodeConfig:
        """Authorization Code 설정을 저장합니다."""
        # 기존 설정이 있는지 확인
        stmt = select(AuthCodeConfigModel).where(
            AuthCodeConfigModel.account_id == str(config.account_id)
        )
        result = await self.session.execute(stmt)
        existing_model = result.scalar_one_or_none()
        
        if existing_model:
            # 업데이트
            existing_model.client_id = config.client_id
            existing_model.client_secret = config.client_secret
            existing_model.redirect_uri = config.redirect_uri
            existing_model.tenant_id = config.tenant_id
            existing_model.updated_at = datetime.utcnow()
            model = existing_model
        else:
            # 새로 생성
            model = AuthCodeConfigModel(
                account_id=str(config.account_id),
                client_id=config.client_id,
                client_secret=config.client_secret,
                redirect_uri=config.redirect_uri,
                tenant_id=config.tenant_id,
            )
            self.session.add(model)
        
        await self.session.commit()
        await self.session.refresh(model)
        
        return self._auth_code_model_to_entity(model)
    
    async def save_device_code_config(self, config: DeviceCodeConfig) -> DeviceCodeConfig:
        """Device Code 설정을 저장합니다."""
        # 기존 설정이 있는지 확인
        stmt = select(DeviceCodeConfigModel).where(
            DeviceCodeConfigModel.account_id == str(config.account_id)
        )
        result = await self.session.execute(stmt)
        existing_model = result.scalar_one_or_none()
        
        if existing_model:
            # 업데이트
            existing_model.client_id = config.client_id
            existing_model.client_secret = config.client_secret
            existing_model.tenant_id = config.tenant_id
            existing_model.updated_at = datetime.utcnow()
            model = existing_model
        else:
            # 새로 생성
            model = DeviceCodeConfigModel(
                account_id=str(config.account_id),
                client_id=config.client_id,
                client_secret=config.client_secret,
                tenant_id=config.tenant_id,
            )
            self.session.add(model)
        
        await self.session.commit()
        await self.session.refresh(model)
        
        return self._device_code_model_to_entity(model)
    
    async def get_auth_code_config(self, account_id: UUID) -> Optional[AuthCodeConfig]:
        """Authorization Code 설정을 조회합니다."""
        stmt = select(AuthCodeConfigModel).where(
            AuthCodeConfigModel.account_id == str(account_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            return None
        
        return self._auth_code_model_to_entity(model)
    
    async def get_device_code_config(self, account_id: UUID) -> Optional[DeviceCodeConfig]:
        """Device Code 설정을 조회합니다."""
        stmt = select(DeviceCodeConfigModel).where(
            DeviceCodeConfigModel.account_id == str(account_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            return None
        
        return self._device_code_model_to_entity(model)
    
    async def delete_auth_code_config(self, account_id: UUID) -> bool:
        """Authorization Code 설정을 삭제합니다."""
        stmt = select(AuthCodeConfigModel).where(
            AuthCodeConfigModel.account_id == str(account_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            return False
        
        await self.session.delete(model)
        await self.session.commit()
        
        return True
    
    async def delete_device_code_config(self, account_id: UUID) -> bool:
        """Device Code 설정을 삭제합니다."""
        stmt = select(DeviceCodeConfigModel).where(
            DeviceCodeConfigModel.account_id == str(account_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            return False
        
        await self.session.delete(model)
        await self.session.commit()
        
        return True
    
    def _auth_code_model_to_entity(self, model: AuthCodeConfigModel) -> AuthCodeConfig:
        """Authorization Code 모델을 엔티티로 변환합니다."""
        return AuthCodeConfig(
            account_id=UUID(model.account_id),
            client_id=model.client_id,
            client_secret=model.client_secret,
            redirect_uri=model.redirect_uri,
            tenant_id=model.tenant_id,
        )
    
    def _device_code_model_to_entity(self, model: DeviceCodeConfigModel) -> DeviceCodeConfig:
        """Device Code 모델을 엔티티로 변환합니다."""
        return DeviceCodeConfig(
            account_id=UUID(model.account_id),
            client_id=model.client_id,
            client_secret=model.client_secret,
            tenant_id=model.tenant_id,
        )


class TokenRepositoryAdapter(TokenRepositoryPort):
    """토큰 Repository 어댑터"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save(self, token: Token) -> Token:
        """토큰을 저장합니다."""
        # 기존 토큰이 있는지 확인
        stmt = select(TokenModel).where(TokenModel.account_id == str(token.account_id))
        result = await self.session.execute(stmt)
        existing_model = result.scalar_one_or_none()
        
        if existing_model:
            # 업데이트
            existing_model.access_token = token.access_token
            existing_model.refresh_token = token.refresh_token
            existing_model.token_type = token.token_type
            existing_model.expires_at = token.expires_at
            existing_model.scope = token.scope
            existing_model.updated_at = datetime.utcnow()
            model = existing_model
        else:
            # 새로 생성
            model = TokenModel(
                account_id=str(token.account_id),
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                token_type=token.token_type,
                expires_at=token.expires_at,
                scope=token.scope,
            )
            self.session.add(model)
        
        await self.session.commit()
        await self.session.refresh(model)
        
        return self._model_to_entity(model)
    
    async def get_by_account_id(self, account_id: UUID) -> Optional[Token]:
        """계정 ID로 토큰을 조회합니다."""
        stmt = select(TokenModel).where(TokenModel.account_id == str(account_id))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            return None
        
        return self._model_to_entity(model)
    
    async def update(self, token: Token) -> Token:
        """토큰을 업데이트합니다."""
        return await self.save(token)
    
    async def delete(self, account_id: UUID) -> bool:
        """토큰을 삭제합니다."""
        stmt = select(TokenModel).where(TokenModel.account_id == str(account_id))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model is None:
            return False
        
        await self.session.delete(model)
        await self.session.commit()
        
        return True
    
    async def list_expired_tokens(self) -> List[Token]:
        """만료된 토큰 목록을 조회합니다."""
        stmt = select(TokenModel).where(TokenModel.expires_at <= datetime.utcnow())
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def list_near_expiry_tokens(self, minutes: int = 5) -> List[Token]:
        """곧 만료될 토큰 목록을 조회합니다."""
        from datetime import timedelta
        threshold = datetime.utcnow() + timedelta(minutes=minutes)
        
        stmt = select(TokenModel).where(
            and_(
                TokenModel.expires_at <= threshold,
                TokenModel.expires_at > datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _model_to_entity(self, model: TokenModel) -> Token:
        """모델을 엔티티로 변환합니다."""
        return Token(
            account_id=UUID(model.account_id),
            access_token=model.access_token,
            refresh_token=model.refresh_token,
            token_type=model.token_type,
            expires_at=model.expires_at,
            scope=model.scope,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
