"""
계정 관리 유즈케이스

Microsoft 365 계정의 등록, 조회, 수정, 삭제 등의 비즈니스 로직을 구현합니다.
"""

from typing import List, Optional
from uuid import UUID

from ..domain.entities import (
    Account,
    AccountStatus,
    AuthCodeConfig,
    AuthType,
    DeviceCodeConfig,
)
from ..domain.ports import (
    AccountRepositoryPort,
    AuthConfigRepositoryPort,
    TokenRepositoryPort,
    LoggerPort,
)


class AccountManagementUseCase:
    """계정 관리 유즈케이스"""
    
    def __init__(
        self,
        account_repository: AccountRepositoryPort,
        auth_config_repository: AuthConfigRepositoryPort,
        logger: LoggerPort,
    ):
        self.account_repository = account_repository
        self.auth_config_repository = auth_config_repository
        self.logger = logger
    
    async def register_account(
        self,
        email: str,
        auth_type: AuthType,
        display_name: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Account:
        """
        새로운 Microsoft 365 계정을 등록합니다.
        
        Args:
            email: 계정 이메일 주소
            auth_type: 인증 방식 (authorization_code 또는 device_code)
            display_name: 표시 이름
            tenant_id: Azure AD 테넌트 ID
            client_id: Azure 애플리케이션 클라이언트 ID
            client_secret: 클라이언트 시크릿 (Authorization Code Flow만 필요)
            redirect_uri: 리다이렉트 URI (Authorization Code Flow만 필요)
            
        Returns:
            생성된 계정 엔티티
            
        Raises:
            ValueError: 중복 계정이거나 필수 정보가 누락된 경우
        """
        self.logger.info(f"계정 등록 시작: {email}, 인증방식: {auth_type}")
        
        # 중복 계정 확인
        if await self.account_repository.exists_by_email(email):
            self.logger.warning(f"중복 계정 등록 시도: {email}")
            raise ValueError(f"이미 등록된 계정입니다: {email}")
        
        # 인증 방식별 필수 정보 검증
        if auth_type == AuthType.AUTHORIZATION_CODE:
            if not all([client_id, client_secret, redirect_uri, tenant_id]):
                raise ValueError("Authorization Code Flow에는 client_id, client_secret, redirect_uri, tenant_id가 필요합니다")
        elif auth_type == AuthType.DEVICE_CODE:
            if not all([client_id, tenant_id]):
                raise ValueError("Device Code Flow에는 client_id, tenant_id가 필요합니다")
        
        # 계정 생성
        account = Account(
            email=email,
            display_name=display_name,
            auth_type=auth_type,
            tenant_id=tenant_id,
        )
        
        # 계정 저장
        created_account = await self.account_repository.create(account)
        
        # 인증 설정 저장
        if auth_type == AuthType.AUTHORIZATION_CODE:
            auth_config = AuthCodeConfig(
                account_id=created_account.id,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                tenant_id=tenant_id,
            )
            await self.auth_config_repository.create_auth_code_config(auth_config)
        elif auth_type == AuthType.DEVICE_CODE:
            auth_config = DeviceCodeConfig(
                account_id=created_account.id,
                client_id=client_id,
                tenant_id=tenant_id,
            )
            await self.auth_config_repository.create_device_code_config(auth_config)
        
        self.logger.info(f"계정 등록 완료: {created_account.id}, {email}")
        return created_account
    
    async def get_account_by_id(self, account_id: UUID) -> Optional[Account]:
        """
        ID로 계정을 조회합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            계정 엔티티 또는 None
        """
        self.logger.debug(f"계정 조회: {account_id}")
        return await self.account_repository.get_by_id(account_id)
    
    async def get_account_by_email(self, email: str) -> Optional[Account]:
        """
        이메일로 계정을 조회합니다.
        
        Args:
            email: 계정 이메일 주소
            
        Returns:
            계정 엔티티 또는 None
        """
        self.logger.debug(f"계정 조회 (이메일): {email}")
        return await self.account_repository.get_by_email(email)
    
    async def list_accounts(self, skip: int = 0, limit: int = 100) -> List[Account]:
        """
        모든 계정 목록을 조회합니다.
        
        Args:
            skip: 건너뛸 개수
            limit: 조회할 최대 개수
            
        Returns:
            계정 목록
        """
        self.logger.debug(f"계정 목록 조회: skip={skip}, limit={limit}")
        return await self.account_repository.list_all(skip=skip, limit=limit)
    
    async def list_active_accounts(self) -> List[Account]:
        """
        활성 계정 목록을 조회합니다.
        
        Returns:
            활성 계정 목록
        """
        self.logger.debug("활성 계정 목록 조회")
        return await self.account_repository.list_active()
    
    async def update_account(
        self,
        account_id: UUID,
        display_name: Optional[str] = None,
        tenant_id: Optional[str] = None,
        auth_type: Optional[AuthType] = None,
    ) -> Optional[Account]:
        """
        계정 정보를 업데이트합니다.
        
        Args:
            account_id: 계정 ID
            display_name: 새로운 표시 이름
            tenant_id: 새로운 테넌트 ID
            auth_type: 새로운 인증 타입
            
        Returns:
            업데이트된 계정 엔티티 또는 None
        """
        self.logger.info(f"계정 정보 업데이트: {account_id}")
        
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            self.logger.warning(f"존재하지 않는 계정 업데이트 시도: {account_id}")
            return None
        
        # 인증 타입 변경 여부 확인
        auth_type_changed = auth_type is not None and auth_type != account.auth_type
        
        # 업데이트할 필드가 있는 경우에만 수정
        updated = False
        if display_name is not None and display_name != account.display_name:
            account.display_name = display_name
            updated = True
        
        if tenant_id is not None and tenant_id != account.tenant_id:
            account.tenant_id = tenant_id
            updated = True
        
        if auth_type_changed:
            self.logger.info(f"인증 타입 변경: {account.auth_type} -> {auth_type}")
            
            # 인증 타입 변경 시 추가 작업 수행
            await self._handle_auth_type_change(account_id, account.auth_type, auth_type)
            
            # 계정 상태를 INACTIVE로 변경 (새로 인증 필요)
            account.status = AccountStatus.INACTIVE
            account.auth_type = auth_type
            account.last_sync_at = None  # 마지막 동기화 시간 초기화
            updated = True
        
        if updated:
            account = await self.account_repository.update(account)
            self.logger.info(f"계정 정보 업데이트 완료: {account_id}")
        else:
            self.logger.debug(f"업데이트할 내용이 없음: {account_id}")
        
        return account
    
    async def _handle_auth_type_change(
        self,
        account_id: UUID,
        old_auth_type: AuthType,
        new_auth_type: AuthType,
    ) -> None:
        """
        인증 타입 변경 시 필요한 정리 작업을 수행합니다.
        
        Args:
            account_id: 계정 ID
            old_auth_type: 기존 인증 타입
            new_auth_type: 새로운 인증 타입
        """
        self.logger.info(f"인증 타입 변경 정리 작업 시작: {account_id}")
        
        # 1. 기존 토큰 삭제 (TokenRepositoryPort가 필요하지만 현재 의존성에 없음)
        # TODO: TokenRepositoryPort 의존성 추가 후 토큰 삭제 로직 구현
        self.logger.warning(f"토큰 삭제 로직 미구현 - 수동으로 삭제 필요: {account_id}")
        
        # 2. 기존 인증 설정 삭제
        try:
            await self.auth_config_repository.delete_config(account_id)
            self.logger.info(f"기존 인증 설정 삭제 완료: {account_id}")
        except Exception as e:
            self.logger.error(f"기존 인증 설정 삭제 실패: {account_id}, 오류: {str(e)}")
        
        # 3. 새로운 인증 설정은 별도로 생성해야 함 (client_id, client_secret 등이 필요)
        self.logger.info(f"새로운 인증 설정은 별도 등록 필요: {new_auth_type}")
        
        self.logger.info(f"인증 타입 변경 정리 작업 완료: {account_id}")
    
    async def list_accounts_by_status(
        self, 
        status: "AccountStatus", 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Account]:
        """
        상태별로 계정 목록을 조회합니다.
        
        Args:
            status: 계정 상태
            skip: 건너뛸 개수
            limit: 조회할 최대 개수
            
        Returns:
            계정 목록
        """
        self.logger.debug(f"상태별 계정 목록 조회: status={status}, skip={skip}, limit={limit}")
        return await self.account_repository.list_by_status(status, skip=skip, limit=limit)
    
    async def list_accounts_by_auth_type(
        self, 
        auth_type: AuthType, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Account]:
        """
        인증 타입별로 계정 목록을 조회합니다.
        
        Args:
            auth_type: 인증 타입
            skip: 건너뛸 개수
            limit: 조회할 최대 개수
            
        Returns:
            계정 목록
        """
        self.logger.debug(f"인증 타입별 계정 목록 조회: auth_type={auth_type}, skip={skip}, limit={limit}")
        return await self.account_repository.list_by_auth_type(auth_type, skip=skip, limit=limit)
    
    async def activate_account(self, account_id: UUID) -> Optional[Account]:
        """
        계정을 활성화합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            활성화된 계정 엔티티 또는 None
        """
        self.logger.info(f"계정 활성화: {account_id}")
        
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            self.logger.warning(f"존재하지 않는 계정 활성화 시도: {account_id}")
            return None
        
        account.activate()
        updated_account = await self.account_repository.update(account)
        
        self.logger.info(f"계정 활성화 완료: {account_id}")
        return updated_account
    
    async def deactivate_account(self, account_id: UUID) -> Optional[Account]:
        """
        계정을 비활성화합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            비활성화된 계정 엔티티 또는 None
        """
        self.logger.info(f"계정 비활성화: {account_id}")
        
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            self.logger.warning(f"존재하지 않는 계정 비활성화 시도: {account_id}")
            return None
        
        account.deactivate()
        updated_account = await self.account_repository.update(account)
        
        self.logger.info(f"계정 비활성화 완료: {account_id}")
        return updated_account
    
    async def mark_account_error(self, account_id: UUID) -> Optional[Account]:
        """
        계정을 오류 상태로 표시합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            오류 상태로 표시된 계정 엔티티 또는 None
        """
        self.logger.warning(f"계정 오류 상태 표시: {account_id}")
        
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            self.logger.warning(f"존재하지 않는 계정 오류 표시 시도: {account_id}")
            return None
        
        account.mark_error()
        updated_account = await self.account_repository.update(account)
        
        self.logger.warning(f"계정 오류 상태 표시 완료: {account_id}")
        return updated_account
    
    async def delete_account(self, account_id: UUID) -> bool:
        """
        계정을 삭제합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            삭제 성공 여부
        """
        self.logger.info(f"계정 삭제: {account_id}")
        
        # 계정 존재 확인
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            self.logger.warning(f"존재하지 않는 계정 삭제 시도: {account_id}")
            return False
        
        # 인증 설정 삭제
        await self.auth_config_repository.delete_config(account_id)
        
        # 계정 삭제
        success = await self.account_repository.delete(account_id)
        
        if success:
            self.logger.info(f"계정 삭제 완료: {account_id}")
        else:
            self.logger.error(f"계정 삭제 실패: {account_id}")
        
        return success
    
    async def get_auth_config(self, account_id: UUID) -> Optional[AuthCodeConfig | DeviceCodeConfig]:
        """
        계정의 인증 설정을 조회합니다.
        
        Args:
            account_id: 계정 ID
            
        Returns:
            인증 설정 엔티티 또는 None
        """
        self.logger.debug(f"인증 설정 조회: {account_id}")
        
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            return None
        
        if account.auth_type == AuthType.AUTHORIZATION_CODE:
            return await self.auth_config_repository.get_auth_code_config(account_id)
        elif account.auth_type == AuthType.DEVICE_CODE:
            return await self.auth_config_repository.get_device_code_config(account_id)
        
        return None
