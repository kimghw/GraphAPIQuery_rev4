"""
Microsoft Graph API 클라이언트 어댑터

Microsoft Graph API와의 통신을 담당하는 어댑터입니다.
OAuth 2.0 인증 플로우와 메일 관련 API를 구현합니다.
"""

import json
from typing import Dict, List, Optional
from urllib.parse import urlencode

import httpx

from core.domain.ports import GraphApiClientPort, LoggerPort


class GraphApiClientAdapter(GraphApiClientPort):
    """Microsoft Graph API 클라이언트 어댑터"""
    
    def __init__(self, logger: LoggerPort):
        self.logger = logger
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.auth_url = "https://login.microsoftonline.com"
        self.timeout = 30.0
    
    async def get_authorization_url(
        self,
        client_id: str,
        tenant_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
    ) -> str:
        """인증 URL을 생성합니다."""
        self.logger.debug(f"인증 URL 생성: client_id={client_id}, tenant_id={tenant_id}")
        
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "response_mode": "query",
        }
        
        url = f"{self.auth_url}/{tenant_id}/oauth2/v2.0/authorize?{urlencode(params)}"
        
        self.logger.debug(f"생성된 인증 URL: {url}")
        return url
    
    async def get_device_code(
        self,
        client_id: str,
        tenant_id: str,
        scope: str,
    ) -> dict:
        """디바이스 코드를 요청합니다."""
        self.logger.debug(f"디바이스 코드 요청: client_id={client_id}, tenant_id={tenant_id}")
        
        url = f"{self.auth_url}/{tenant_id}/oauth2/v2.0/devicecode"
        
        data = {
            "client_id": client_id,
            "scope": scope,
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_msg = f"디바이스 코드 요청 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            self.logger.debug(f"디바이스 코드 요청 성공: device_code={result.get('device_code', 'N/A')}")
            return result
    
    async def exchange_code_for_token(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        redirect_uri: str,
        code: str,
    ) -> dict:
        """인증 코드를 토큰으로 교환합니다."""
        self.logger.debug(f"토큰 교환: client_id={client_id}, tenant_id={tenant_id}")
        
        url = f"{self.auth_url}/{tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_msg = f"토큰 교환 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            self.logger.debug("토큰 교환 성공")
            return result
    
    async def poll_device_code(
        self,
        client_id: str,
        tenant_id: str,
        device_code: str,
    ) -> dict:
        """디바이스 코드를 폴링합니다."""
        self.logger.debug(f"디바이스 코드 폴링: client_id={client_id}, tenant_id={tenant_id}")
        
        url = f"{self.auth_url}/{tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": client_id,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_code = error_data.get("error", "unknown_error")
                error_description = error_data.get("error_description", response.text)
                
                # 특정 오류는 예외로 처리하지 않고 상위에서 처리하도록 함
                if error_code in ["authorization_pending", "slow_down", "access_denied", "expired_token"]:
                    raise Exception(error_code)
                
                error_msg = f"디바이스 코드 폴링 실패: {response.status_code} - {error_description}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            self.logger.debug("디바이스 코드 폴링 성공")
            return result
    
    async def refresh_token(
        self,
        client_id: str,
        client_secret: Optional[str],
        tenant_id: str,
        refresh_token: str,
    ) -> dict:
        """토큰을 갱신합니다."""
        self.logger.debug(f"토큰 갱신: client_id={client_id}, tenant_id={tenant_id}")
        
        url = f"{self.auth_url}/{tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        
        # Device Code Flow의 경우 client_secret이 없을 수 있음
        if client_secret:
            data["client_secret"] = client_secret
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_msg = f"토큰 갱신 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            self.logger.debug("토큰 갱신 성공")
            return result
    
    async def get_user_profile(self, access_token: str) -> dict:
        """사용자 프로필을 조회합니다."""
        self.logger.debug("사용자 프로필 조회")
        
        url = f"{self.base_url}/me"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"사용자 프로필 조회 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            self.logger.debug(f"사용자 프로필 조회 성공: {result.get('userPrincipalName', 'N/A')}")
            return result
    
    async def list_messages(
        self,
        access_token: str,
        top: int = 50,
        skip: int = 0,
        filter_query: Optional[str] = None,
        order_by: Optional[str] = None,
    ) -> dict:
        """메시지 목록을 조회합니다."""
        self.logger.debug(f"메시지 목록 조회: top={top}, skip={skip}")
        
        url = f"{self.base_url}/me/messages"
        
        params = {
            "$top": top,
            "$skip": skip,
        }
        
        if filter_query:
            params["$filter"] = filter_query
        
        if order_by:
            params["$orderby"] = order_by
        else:
            params["$orderby"] = "receivedDateTime desc"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                error_msg = f"메시지 목록 조회 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            message_count = len(result.get("value", []))
            self.logger.debug(f"메시지 목록 조회 성공: {message_count}개 메시지")
            return result
    
    async def get_message(self, access_token: str, message_id: str) -> dict:
        """특정 메시지를 조회합니다."""
        self.logger.debug(f"메시지 조회: message_id={message_id}")
        
        url = f"{self.base_url}/me/messages/{message_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"메시지 조회 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            self.logger.debug(f"메시지 조회 성공: {result.get('subject', 'N/A')}")
            return result
    
    async def send_message(self, access_token: str, message_data: dict) -> dict:
        """메시지를 발송합니다."""
        self.logger.debug(f"메시지 발송: subject={message_data.get('message', {}).get('subject', 'N/A')}")
        
        url = f"{self.base_url}/me/sendMail"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers=headers,
                json=message_data
            )
            
            if response.status_code not in [200, 202]:
                error_msg = f"메시지 발송 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            # 발송 성공 시 응답 본문이 없을 수 있음
            result = response.json() if response.content else {"status": "sent"}
            self.logger.debug("메시지 발송 성공")
            return result
    
    async def get_delta_messages(self, access_token: str, delta_link: str) -> dict:
        """델타 메시지를 조회합니다."""
        self.logger.debug("델타 메시지 조회")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(delta_link, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"델타 메시지 조회 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            message_count = len(result.get("value", []))
            self.logger.debug(f"델타 메시지 조회 성공: {message_count}개 변경사항")
            return result
    
    async def create_subscription(
        self,
        access_token: str,
        resource: str,
        change_types: List[str],
        notification_url: str,
        expiration_datetime: str,
        client_state: Optional[str] = None,
    ) -> dict:
        """웹훅 구독을 생성합니다."""
        self.logger.debug(f"웹훅 구독 생성: resource={resource}")
        
        url = f"{self.base_url}/subscriptions"
        
        subscription_data = {
            "changeType": ",".join(change_types),
            "notificationUrl": notification_url,
            "resource": resource,
            "expirationDateTime": expiration_datetime,
        }
        
        if client_state:
            subscription_data["clientState"] = client_state
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers=headers,
                json=subscription_data
            )
            
            if response.status_code != 201:
                error_msg = f"웹훅 구독 생성 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            self.logger.debug(f"웹훅 구독 생성 성공: subscription_id={result.get('id', 'N/A')}")
            return result
    
    async def update_subscription(
        self,
        access_token: str,
        subscription_id: str,
        expiration_datetime: str,
    ) -> dict:
        """웹훅 구독을 업데이트합니다."""
        self.logger.debug(f"웹훅 구독 업데이트: subscription_id={subscription_id}")
        
        url = f"{self.base_url}/subscriptions/{subscription_id}"
        
        update_data = {
            "expirationDateTime": expiration_datetime,
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.patch(
                url,
                headers=headers,
                json=update_data
            )
            
            if response.status_code != 200:
                error_msg = f"웹훅 구독 업데이트 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            self.logger.debug("웹훅 구독 업데이트 성공")
            return result
    
    async def delete_subscription(
        self,
        access_token: str,
        subscription_id: str,
    ) -> bool:
        """웹훅 구독을 삭제합니다."""
        self.logger.debug(f"웹훅 구독 삭제: subscription_id={subscription_id}")
        
        url = f"{self.base_url}/subscriptions/{subscription_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(url, headers=headers)
            
            if response.status_code != 204:
                error_msg = f"웹훅 구독 삭제 실패: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return False
            
            self.logger.debug("웹훅 구독 삭제 성공")
            return True
