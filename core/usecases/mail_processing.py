"""
메일 처리 유즈케이스

Microsoft 365 메일 조회, 발송, 동기화 등의 비즈니스 로직을 구현합니다.
데이터베이스에서 계정 정보와 토큰을 조회하여 메일 처리를 수행합니다.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from ..domain.entities import (
    Account,
    DeltaLink,
    Mail,
    SyncHistory,
    SyncStatus,
    Token,
)
from ..domain.ports import (
    AccountRepositoryPort,
    DeltaLinkRepositoryPort,
    EncryptionServicePort,
    ExternalApiClientPort,
    GraphApiClientPort,
    LoggerPort,
    MailRepositoryPort,
    SyncHistoryRepositoryPort,
    TokenRepositoryPort,
)


class MailProcessingUseCase:
    """메일 처리 유즈케이스"""
    
    def __init__(
        self,
        account_repository: AccountRepositoryPort,
        token_repository: TokenRepositoryPort,
        mail_repository: MailRepositoryPort,
        sync_history_repository: SyncHistoryRepositoryPort,
        delta_link_repository: DeltaLinkRepositoryPort,
        graph_api_client: GraphApiClientPort,
        encryption_service: EncryptionServicePort,
        external_api_client: ExternalApiClientPort,
        logger: LoggerPort,
    ):
        self.account_repository = account_repository
        self.token_repository = token_repository
        self.mail_repository = mail_repository
        self.sync_history_repository = sync_history_repository
        self.delta_link_repository = delta_link_repository
        self.graph_api_client = graph_api_client
        self.encryption_service = encryption_service
        self.external_api_client = external_api_client
        self.logger = logger
    
    async def list_mails(
        self,
        account_id: UUID,
        top: int = 50,
        skip: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        filter_query: Optional[str] = None,
        order_by: Optional[str] = None,
    ) -> List[Mail]:
        """
        계정의 메일 목록을 조회합니다.
        데이터베이스에서 토큰을 가져와서 Graph API를 호출합니다.
        
        Args:
            account_id: 계정 ID
            top: 조회할 메일 수
            skip: 건너뛸 메일 수
            start_date: 시작 날짜
            end_date: 종료 날짜
            filter_query: 필터 쿼리
            order_by: 정렬 기준
            
        Returns:
            메일 목록
            
        Raises:
            ValueError: 계정이나 토큰이 없는 경우
        """
        self.logger.info(f"메일 목록 조회 시작: {account_id}")
        
        # 계정 조회
        account = await self.account_repository.get_by_id(account_id)
        if not account:
            raise ValueError(f"계정을 찾을 수 없습니다: {account_id}")
        
        if not account.can_sync():
            raise ValueError(f"동기화할 수 없는 계정 상태입니다: {account.status}")
        
        # 데이터베이스에서 토큰 조회
        token = await self.token_repository.get_by_account_id(account_id)
        if not token:
            raise ValueError(f"토큰을 찾을 수 없습니다: {account_id}")
        
        # 토큰 만료 확인 및 갱신
        if token.is_expired():
            self.logger.info(f"토큰이 만료되어 갱신 시도: {account_id}")
            # 토큰 갱신은 AuthenticationUseCase에서 처리
            from .authentication import AuthenticationUseCase
            auth_usecase = AuthenticationUseCase(
                self.account_repository,
                None,  # auth_config_repository는 여기서 필요없음
                self.token_repository,
                self.graph_api_client,
                self.encryption_service,
                None,  # cache_service는 여기서 필요없음
                self.logger,
            )
            token = await auth_usecase.refresh_token(account_id)
            if not token:
                raise ValueError(f"토큰 갱신에 실패했습니다: {account_id}")
        
        try:
            # 액세스 토큰 복호화
            decrypted_access_token = await self.encryption_service.decrypt(
                token.access_token
            )
            
            # 날짜 필터 구성
            if start_date or end_date:
                date_filter = self._build_date_filter(start_date, end_date)
                if filter_query:
                    filter_query = f"({filter_query}) and ({date_filter})"
                else:
                    filter_query = date_filter
            
            # Graph API로 메일 목록 조회
            response = await self.graph_api_client.list_messages(
                access_token=decrypted_access_token,
                top=top,
                skip=skip,
                filter_query=filter_query,
                order_by=order_by or "receivedDateTime desc",
            )
            
            # 응답 데이터를 Mail 엔티티로 변환
            mails = []
            for message_data in response.get('value', []):
                mail = self._convert_message_to_mail(account_id, message_data)
                mails.append(mail)
            
            self.logger.info(f"메일 목록 조회 완료: {account_id}, {len(mails)}개")
            return mails
            
        except Exception as e:
            self.logger.error(f"메일 목록 조회 실패: {account_id}, 오류: {str(e)}")
            raise
    
    async def get_mail_by_message_id(
        self,
        account_id: UUID,
        message_id: str,
    ) -> Optional[Mail]:
        """
        특정 메시지 ID로 메일을 조회합니다.
        
        Args:
            account_id: 계정 ID
            message_id: 메시지 ID
            
        Returns:
            메일 엔티티 또는 None
        """
        self.logger.debug(f"메일 조회: {account_id}, {message_id}")
        
        # 먼저 데이터베이스에서 조회
        existing_mail = await self.mail_repository.get_by_message_id(account_id, message_id)
        if existing_mail:
            return existing_mail
        
        # 데이터베이스에 없으면 Graph API에서 조회
        account = await self.account_repository.get_by_id(account_id)
        if not account or not account.can_sync():
            return None
        
        token = await self.token_repository.get_by_account_id(account_id)
        if not token:
            return None
        
        # 토큰 만료 확인
        if token.is_expired():
            return None
        
        try:
            decrypted_access_token = await self.encryption_service.decrypt(
                token.access_token
            )
            
            message_data = await self.graph_api_client.get_message(
                access_token=decrypted_access_token,
                message_id=message_id,
            )
            
            # Mail 엔티티로 변환 및 저장
            mail = self._convert_message_to_mail(account_id, message_data)
            saved_mail = await self.mail_repository.create(mail)
            
            self.logger.debug(f"메일 조회 및 저장 완료: {account_id}, {message_id}")
            return saved_mail
            
        except Exception as e:
            self.logger.error(f"메일 조회 실패: {account_id}, {message_id}, 오류: {str(e)}")
            return None
    
    async def send_mail(
        self,
        account_id: UUID,
        to_recipients: List[str],
        subject: str,
        body_content: str,
        body_content_type: str = "HTML",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        importance: str = "normal",
    ) -> bool:
        """
        메일을 발송합니다.
        
        Args:
            account_id: 계정 ID
            to_recipients: 수신자 목록
            subject: 제목
            body_content: 본문 내용
            body_content_type: 본문 타입 (HTML, Text)
            cc_recipients: 참조 수신자 목록
            bcc_recipients: 숨은참조 수신자 목록
            importance: 중요도 (low, normal, high)
            
        Returns:
            발송 성공 여부
        """
        self.logger.info(f"메일 발송 시작: {account_id}")
        
        # 계정 및 토큰 조회
        account = await self.account_repository.get_by_id(account_id)
        if not account or not account.can_sync():
            raise ValueError(f"메일을 발송할 수 없는 계정 상태입니다: {account_id}")
        
        token = await self.token_repository.get_by_account_id(account_id)
        if not token:
            raise ValueError(f"토큰을 찾을 수 없습니다: {account_id}")
        
        # 토큰 만료 확인
        if token.is_expired():
            raise ValueError(f"토큰이 만료되었습니다: {account_id}")
        
        try:
            decrypted_access_token = await self.encryption_service.decrypt(
                token.access_token
            )
            
            # 메일 데이터 구성
            message_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": body_content_type,
                        "content": body_content,
                    },
                    "toRecipients": [
                        {"emailAddress": {"address": email}} for email in to_recipients
                    ],
                    "importance": importance,
                }
            }
            
            if cc_recipients:
                message_data["message"]["ccRecipients"] = [
                    {"emailAddress": {"address": email}} for email in cc_recipients
                ]
            
            if bcc_recipients:
                message_data["message"]["bccRecipients"] = [
                    {"emailAddress": {"address": email}} for email in bcc_recipients
                ]
            
            # Graph API로 메일 발송
            response = await self.graph_api_client.send_message(
                access_token=decrypted_access_token,
                message_data=message_data,
            )
            
            self.logger.info(f"메일 발송 완료: {account_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"메일 발송 실패: {account_id}, 오류: {str(e)}")
            return False
    
    async def sync_mails(
        self,
        account_id: UUID,
        use_delta: bool = True,
        batch_size: int = 100,
    ) -> SyncHistory:
        """
        메일을 동기화합니다.
        
        Args:
            account_id: 계정 ID
            use_delta: 델타 동기화 사용 여부
            batch_size: 배치 크기
            
        Returns:
            동기화 이력
        """
        self.logger.info(f"메일 동기화 시작: {account_id}, 델타: {use_delta}")
        
        # 동기화 이력 생성
        sync_history = SyncHistory(
            account_id=account_id,
            sync_type="delta" if use_delta else "full",
            status=SyncStatus.PROCESSING,
        )
        sync_history = await self.sync_history_repository.create(sync_history)
        
        try:
            # 계정 및 토큰 조회
            account = await self.account_repository.get_by_id(account_id)
            if not account or not account.can_sync():
                raise ValueError(f"동기화할 수 없는 계정 상태입니다: {account_id}")
            
            token = await self.token_repository.get_by_account_id(account_id)
            if not token:
                raise ValueError(f"토큰을 찾을 수 없습니다: {account_id}")
            
            # 토큰 만료 확인
            if token.is_expired():
                raise ValueError(f"토큰이 만료되었습니다: {account_id}")
            
            decrypted_access_token = await self.encryption_service.decrypt(
                token.access_token
            )
            
            processed_count = 0
            error_count = 0
            
            if use_delta:
                # 델타 동기화
                delta_link_entity = await self.delta_link_repository.get_by_account_id(account_id)
                if delta_link_entity:
                    # 기존 델타 링크로 동기화
                    response = await self.graph_api_client.get_delta_messages(
                        access_token=decrypted_access_token,
                        delta_link=delta_link_entity.delta_link,
                    )
                else:
                    # 초기 델타 동기화
                    response = await self.graph_api_client.list_messages(
                        access_token=decrypted_access_token,
                        top=batch_size,
                    )
                
                # 메일 처리
                for message_data in response.get('value', []):
                    try:
                        await self._process_message(account_id, message_data)
                        processed_count += 1
                    except Exception as e:
                        self.logger.error(f"메시지 처리 오류: {message_data.get('id')}, {str(e)}")
                        error_count += 1
                
                # 새 델타 링크 저장
                new_delta_link = response.get('@odata.deltaLink')
                if new_delta_link:
                    if delta_link_entity:
                        delta_link_entity.update_link(new_delta_link)
                        await self.delta_link_repository.update(delta_link_entity)
                    else:
                        new_delta_link_entity = DeltaLink(
                            account_id=account_id,
                            delta_link=new_delta_link,
                        )
                        await self.delta_link_repository.save(new_delta_link_entity)
            
            else:
                # 전체 동기화
                skip = 0
                while True:
                    response = await self.graph_api_client.list_messages(
                        access_token=decrypted_access_token,
                        top=batch_size,
                        skip=skip,
                        order_by="receivedDateTime desc",
                    )
                    
                    messages = response.get('value', [])
                    if not messages:
                        break
                    
                    for message_data in messages:
                        try:
                            await self._process_message(account_id, message_data)
                            processed_count += 1
                        except Exception as e:
                            self.logger.error(f"메시지 처리 오류: {message_data.get('id')}, {str(e)}")
                            error_count += 1
                    
                    skip += batch_size
                    
                    # 배치 크기보다 적게 반환되면 마지막 페이지
                    if len(messages) < batch_size:
                        break
            
            # 동기화 완료 처리
            sync_history.processed_count = processed_count
            sync_history.error_count = error_count
            sync_history.mark_as_completed()
            
            # 계정 마지막 동기화 시간 업데이트
            account.last_sync_at = datetime.utcnow()
            await self.account_repository.update(account)
            
            self.logger.info(f"메일 동기화 완료: {account_id}, 처리: {processed_count}, 오류: {error_count}")
            
        except Exception as e:
            self.logger.error(f"메일 동기화 실패: {account_id}, 오류: {str(e)}")
            sync_history.mark_as_failed(str(e))
        
        # 동기화 이력 업데이트
        return await self.sync_history_repository.update(sync_history)
    
    async def _process_message(self, account_id: UUID, message_data: Dict) -> None:
        """
        메시지 데이터를 처리합니다.
        
        Args:
            account_id: 계정 ID
            message_data: Graph API 메시지 데이터
        """
        message_id = message_data.get('id')
        
        # 이미 존재하는 메일인지 확인
        existing_mail = await self.mail_repository.exists_by_message_id(account_id, message_id)
        if existing_mail:
            self.logger.debug(f"이미 존재하는 메일: {message_id}")
            return
        
        # Mail 엔티티로 변환
        mail = self._convert_message_to_mail(account_id, message_data)
        
        # 데이터베이스에 저장
        saved_mail = await self.mail_repository.create(mail)
        
        # 외부 API로 전송
        try:
            mail_data = {
                "account_id": str(account_id),
                "message_id": message_id,
                "subject": mail.subject,
                "sender": mail.sender,
                "recipients": mail.recipients,
                "received_at": mail.received_at.isoformat(),
                "body_preview": mail.body_preview,
            }
            
            success = await self.external_api_client.send_mail_data(mail_data)
            if success:
                saved_mail.mark_as_processed()
                await self.mail_repository.update(saved_mail)
                self.logger.debug(f"메일 외부 전송 완료: {message_id}")
            else:
                self.logger.warning(f"메일 외부 전송 실패: {message_id}")
                
        except Exception as e:
            self.logger.error(f"메일 외부 전송 오류: {message_id}, {str(e)}")
    
    def _convert_message_to_mail(self, account_id: UUID, message_data: Dict) -> Mail:
        """
        Graph API 메시지 데이터를 Mail 엔티티로 변환합니다.
        
        Args:
            account_id: 계정 ID
            message_data: Graph API 메시지 데이터
            
        Returns:
            Mail 엔티티
        """
        # 수신자 정보 추출
        to_recipients = []
        cc_recipients = []
        bcc_recipients = []
        
        for recipient in message_data.get('toRecipients', []):
            email = recipient.get('emailAddress', {}).get('address')
            if email:
                to_recipients.append(email)
        
        for recipient in message_data.get('ccRecipients', []):
            email = recipient.get('emailAddress', {}).get('address')
            if email:
                cc_recipients.append(email)
        
        for recipient in message_data.get('bccRecipients', []):
            email = recipient.get('emailAddress', {}).get('address')
            if email:
                bcc_recipients.append(email)
        
        # 발신자 정보 추출
        sender = None
        sender_data = message_data.get('sender', {}).get('emailAddress')
        if sender_data:
            sender = sender_data.get('address')
        
        # 본문 정보 추출
        body = message_data.get('body', {})
        body_content = body.get('content')
        body_content_type = body.get('contentType')
        
        # 날짜 파싱
        received_datetime_str = message_data.get('receivedDateTime')
        received_at = datetime.fromisoformat(received_datetime_str.replace('Z', '+00:00')) if received_datetime_str else datetime.utcnow()
        
        sent_datetime_str = message_data.get('sentDateTime')
        sent_at = datetime.fromisoformat(sent_datetime_str.replace('Z', '+00:00')) if sent_datetime_str else None
        
        return Mail(
            account_id=account_id,
            message_id=message_data.get('id'),
            subject=message_data.get('subject'),
            sender=sender,
            recipients=to_recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            body_preview=message_data.get('bodyPreview'),
            body_content=body_content,
            body_content_type=body_content_type,
            importance=message_data.get('importance'),
            is_read=message_data.get('isRead', False),
            has_attachments=message_data.get('hasAttachments', False),
            received_at=received_at,
            sent_at=sent_at,
        )
    
    def _build_date_filter(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> str:
        """
        날짜 필터 쿼리를 구성합니다.
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            OData 필터 쿼리
        """
        filters = []
        
        if start_date:
            start_str = start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            filters.append(f"receivedDateTime ge {start_str}")
        
        if end_date:
            end_str = end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            filters.append(f"receivedDateTime le {end_str}")
        
        return " and ".join(filters)
    
    async def get_sync_history(
        self,
        account_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SyncHistory]:
        """
        계정의 동기화 이력을 조회합니다.
        
        Args:
            account_id: 계정 ID
            skip: 건너뛸 개수
            limit: 조회할 최대 개수
            
        Returns:
            동기화 이력 목록
        """
        self.logger.debug(f"동기화 이력 조회: {account_id}")
        return await self.sync_history_repository.list_by_account(
            account_id=account_id,
            skip=skip,
            limit=limit,
        )
    
    async def get_stored_mails(
        self,
        account_id: UUID,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Mail]:
        """
        데이터베이스에 저장된 메일 목록을 조회합니다.
        
        Args:
            account_id: 계정 ID
            skip: 건너뛸 개수
            limit: 조회할 최대 개수
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            저장된 메일 목록
        """
        self.logger.debug(f"저장된 메일 조회: {account_id}")
        return await self.mail_repository.list_by_account(
            account_id=account_id,
            skip=skip,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )
