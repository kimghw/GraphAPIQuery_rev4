"""
FastAPI 인증 라우터

Authorization Code Flow 콜백 처리를 위한 웹 인터페이스입니다.
"""

from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.entities import AuthType
from core.usecases.authentication import AuthenticationUseCase
from adapters.db.database import get_db_session
from adapters.db.repositories import (
    AccountRepositoryAdapter,
    AuthConfigRepositoryAdapter,
    TokenRepositoryAdapter,
)
from adapters.db.cache_repository import DatabaseCacheServiceAdapter
from adapters.external.graph_api_client import GraphApiClientAdapter
from adapters.external.encryption_service import EncryptionServiceAdapter
from adapters.logger import create_logger
from config.adapters import get_config

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = create_logger("auth_router")


@router.get("/start")
async def start_auth(
    email: str = Query(..., description="계정 이메일"),
    flow: str = Query("authorization_code", description="인증 플로우 타입"),
    session: AsyncSession = Depends(get_db_session),
):
    """인증 플로우를 시작합니다."""
    logger.info(f"인증 시작 요청: email={email}, flow={flow}")
    
    try:
        # Repository 및 서비스 생성
        account_repo = AccountRepositoryAdapter(session)
        auth_config_repo = AuthConfigRepositoryAdapter(session)
        token_repo = TokenRepositoryAdapter(session)
        
        # 계정 조회
        account = await account_repo.get_by_email(email)
        if not account:
            logger.error(f"계정을 찾을 수 없음: {email}")
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # 인증 타입 확인
        if flow == "authorization_code" and account.auth_type != AuthType.AUTHORIZATION_CODE:
            logger.error(f"잘못된 인증 타입: {account.auth_type}")
            raise HTTPException(
                status_code=400, 
                detail="Authorization Code Flow가 아닙니다"
            )
        elif flow == "device_code" and account.auth_type != AuthType.DEVICE_CODE:
            logger.error(f"잘못된 인증 타입: {account.auth_type}")
            raise HTTPException(
                status_code=400,
                detail="Device Code Flow가 아닙니다"
            )
        
        # 서비스 생성
        config = get_config()
        graph_client = GraphApiClientAdapter(logger)
        encryption_service = EncryptionServiceAdapter(
            config.get_encryption_key(),
            logger
        )
        cache_service = DatabaseCacheServiceAdapter(session, logger)
        
        # 유즈케이스 생성
        auth_usecase = AuthenticationUseCase(
            account_repository=account_repo,
            auth_config_repository=auth_config_repo,
            token_repository=token_repo,
            graph_api_client=graph_client,
            encryption_service=encryption_service,
            cache_service=cache_service,
            logger=logger,
        )
        
        if flow == "authorization_code":
            # Authorization Code Flow 시작
            logger.info(f"Authorization Code Flow 시작: {account.id}")
            auth_url, state = await auth_usecase.start_authorization_code_flow(
                account.id,
                scope="https://graph.microsoft.com/.default"
            )
            
            logger.info(f"인증 URL 생성 완료: state={state}")
            
            # 리다이렉트
            return RedirectResponse(url=auth_url)
        
        elif flow == "device_code":
            # Device Code Flow - HTML 페이지 반환
            logger.info(f"Device Code Flow 시작: {account.id}")
            device_info = await auth_usecase.start_device_code_flow(
                account.id,
                scope="https://graph.microsoft.com/.default"
            )
            
            logger.info(f"Device Code 생성 완료: user_code={device_info['user_code']}")
            
            # HTML 응답
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Device Code 인증</title>
                <style>
                    body {{ font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto; }}
                    .code {{ font-size: 32px; font-weight: bold; color: #0078d4; margin: 20px 0; }}
                    .info {{ background: #f0f0f0; padding: 20px; border-radius: 8px; }}
                    .step {{ margin: 10px 0; }}
                </style>
            </head>
            <body>
                <h1>Device Code 인증</h1>
                <div class="info">
                    <p class="step">1. 다음 URL로 이동하세요:</p>
                    <p><a href="{device_info['verification_uri']}" target="_blank">{device_info['verification_uri']}</a></p>
                    
                    <p class="step">2. 다음 코드를 입력하세요:</p>
                    <p class="code">{device_info['user_code']}</p>
                    
                    <p class="step">3. Microsoft 계정으로 로그인하고 권한을 승인하세요.</p>
                    
                    <p class="step">4. 인증이 완료되면 아래 링크를 클릭하세요:</p>
                    <p><a href="/auth/poll-device?device_code={device_info['device_code']}">인증 확인</a></p>
                </div>
                
                <p style="margin-top: 40px; color: #666;">
                    계정: {email}<br>
                    만료: {device_info.get('expires_in', 900)}초 후
                </p>
            </body>
            </html>
            """
            
            return HTMLResponse(content=html_content)
        
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 인증 플로우입니다")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"인증 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def auth_callback(
    code: Optional[str] = Query(None, description="인증 코드"),
    state: Optional[str] = Query(None, description="State 값"),
    error: Optional[str] = Query(None, description="오류 코드"),
    error_description: Optional[str] = Query(None, description="오류 설명"),
    session: AsyncSession = Depends(get_db_session),
):
    """Authorization Code Flow 콜백을 처리합니다."""
    logger.info(f"인증 콜백 수신: code={code[:10] if code else None}..., state={state}, error={error}")
    
    # 오류 처리
    if error:
        logger.error(f"인증 오류: {error} - {error_description}")
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>인증 오류</title>
            <style>
                body {{ font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto; }}
                .error {{ color: #d32f2f; background: #ffebee; padding: 20px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <h1>인증 오류</h1>
            <div class="error">
                <p><strong>오류 코드:</strong> {error}</p>
                <p><strong>설명:</strong> {error_description}</p>
            </div>
            <p style="margin-top: 20px;">
                <a href="/">홈으로 돌아가기</a>
            </p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)
    
    # 필수 파라미터 확인
    if not code or not state:
        logger.error("필수 파라미터 누락")
        raise HTTPException(status_code=400, detail="필수 파라미터가 누락되었습니다")
    
    try:
        # Repository 및 서비스 생성
        account_repo = AccountRepositoryAdapter(session)
        auth_config_repo = AuthConfigRepositoryAdapter(session)
        token_repo = TokenRepositoryAdapter(session)
        
        # 서비스 생성
        config = get_config()
        graph_client = GraphApiClientAdapter(logger)
        encryption_service = EncryptionServiceAdapter(
            config.get_encryption_key(),
            logger
        )
        cache_service = DatabaseCacheServiceAdapter(session, logger)
        
        # 유즈케이스 생성
        auth_usecase = AuthenticationUseCase(
            account_repository=account_repo,
            auth_config_repository=auth_config_repo,
            token_repository=token_repo,
            graph_api_client=graph_client,
            encryption_service=encryption_service,
            cache_service=cache_service,
            logger=logger,
        )
        
        # 인증 완료 처리
        logger.info(f"인증 코드 교환 시작: state={state}")
        token = await auth_usecase.complete_authorization_code_flow(
            code=code,
            state=state,
            scope="https://graph.microsoft.com/.default"
        )
        
        logger.info(f"토큰 발급 완료: account_id={token.account_id}")
        
        # 계정 정보 조회
        account = await account_repo.get_by_id(token.account_id)
        
        # 성공 HTML 응답
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>인증 성공</title>
            <style>
                body {{ font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto; }}
                .success {{ color: #2e7d32; background: #e8f5e9; padding: 20px; border-radius: 8px; }}
                .info {{ background: #f0f0f0; padding: 20px; border-radius: 8px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1>인증 성공!</h1>
            <div class="success">
                <p>Microsoft 365 인증이 성공적으로 완료되었습니다.</p>
            </div>
            
            <div class="info">
                <h2>계정 정보</h2>
                <p><strong>이메일:</strong> {account.email}</p>
                <p><strong>표시 이름:</strong> {account.display_name or '-'}</p>
                <p><strong>상태:</strong> {account.status.value}</p>
                <p><strong>토큰 만료:</strong> {token.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <p style="margin-top: 30px;">
                이제 이 창을 닫고 CLI에서 다음 명령어를 사용할 수 있습니다:<br>
                <code style="background: #f0f0f0; padding: 5px;">python main.py auth get-profile --email {account.email}</code>
            </p>
        </body>
        </html>
        """
        
        return HTMLResponse(content=success_html)
        
    except Exception as e:
        logger.error(f"인증 콜백 처리 오류: {str(e)}")
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>인증 오류</title>
            <style>
                body {{ font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto; }}
                .error {{ color: #d32f2f; background: #ffebee; padding: 20px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <h1>인증 오류</h1>
            <div class="error">
                <p>{str(e)}</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)


@router.get("/poll-device")
async def poll_device_code(
    device_code: str = Query(..., description="디바이스 코드"),
    session: AsyncSession = Depends(get_db_session),
):
    """Device Code Flow 폴링을 처리합니다."""
    logger.info(f"Device Code 폴링 요청: device_code={device_code[:10]}...")
    
    try:
        # Repository 및 서비스 생성
        account_repo = AccountRepositoryAdapter(session)
        auth_config_repo = AuthConfigRepositoryAdapter(session)
        token_repo = TokenRepositoryAdapter(session)
        
        # 서비스 생성
        config = get_config()
        graph_client = GraphApiClientAdapter(logger)
        encryption_service = EncryptionServiceAdapter(
            config.get_encryption_key(),
            logger
        )
        cache_service = DatabaseCacheServiceAdapter(session, logger)
        
        # 유즈케이스 생성
        auth_usecase = AuthenticationUseCase(
            account_repository=account_repo,
            auth_config_repository=auth_config_repo,
            token_repository=token_repo,
            graph_api_client=graph_client,
            encryption_service=encryption_service,
            cache_service=cache_service,
            logger=logger,
        )
        
        # 폴링 시도 (한 번만)
        logger.info("Device Code 폴링 시작")
        try:
            token = await auth_usecase.poll_device_code_flow(
                device_code=device_code,
                scope="https://graph.microsoft.com/.default",
                max_attempts=1,  # 한 번만 시도
                interval=0
            )
            
            logger.info(f"Device Code 인증 성공: account_id={token.account_id}")
            
            # 계정 정보 조회
            account = await account_repo.get_by_id(token.account_id)
            
            # 성공 HTML
            success_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>인증 성공</title>
                <style>
                    body {{ font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto; }}
                    .success {{ color: #2e7d32; background: #e8f5e9; padding: 20px; border-radius: 8px; }}
                    .info {{ background: #f0f0f0; padding: 20px; border-radius: 8px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <h1>Device Code 인증 성공!</h1>
                <div class="success">
                    <p>Microsoft 365 인증이 성공적으로 완료되었습니다.</p>
                </div>
                
                <div class="info">
                    <h2>계정 정보</h2>
                    <p><strong>이메일:</strong> {account.email}</p>
                    <p><strong>표시 이름:</strong> {account.display_name or '-'}</p>
                    <p><strong>상태:</strong> {account.status.value}</p>
                </div>
            </body>
            </html>
            """
            
            return HTMLResponse(content=success_html)
            
        except TimeoutError:
            logger.info("Device Code 아직 인증되지 않음")
            # 대기 중 HTML
            waiting_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>인증 대기 중</title>
                <meta http-equiv="refresh" content="5">
                <style>
                    body {{ font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto; }}
                    .waiting {{ color: #1976d2; background: #e3f2fd; padding: 20px; border-radius: 8px; }}
                </style>
            </head>
            <body>
                <h1>인증 대기 중...</h1>
                <div class="waiting">
                    <p>아직 인증이 완료되지 않았습니다.</p>
                    <p>Microsoft 페이지에서 인증을 완료해주세요.</p>
                    <p style="font-size: 14px; color: #666;">5초 후 자동으로 새로고침됩니다...</p>
                </div>
                
                <p style="margin-top: 20px;">
                    <a href="/auth/poll-device?device_code={device_code}">수동으로 확인</a>
                </p>
            </body>
            </html>
            """
            
            return HTMLResponse(content=waiting_html)
            
        except ValueError as e:
            logger.error(f"Device Code 인증 실패: {str(e)}")
            # 오류 HTML
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>인증 실패</title>
                <style>
                    body {{ font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto; }}
                    .error {{ color: #d32f2f; background: #ffebee; padding: 20px; border-radius: 8px; }}
                </style>
            </head>
            <body>
                <h1>인증 실패</h1>
                <div class="error">
                    <p>{str(e)}</p>
                </div>
            </body>
            </html>
            """
            
            return HTMLResponse(content=error_html, status_code=400)
            
    except Exception as e:
        logger.error(f"Device Code 폴링 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{email}")
async def get_auth_status(
    email: str,
    session: AsyncSession = Depends(get_db_session),
):
    """계정의 인증 상태를 조회합니다."""
    logger.info(f"인증 상태 조회: {email}")
    
    try:
        account_repo = AccountRepositoryAdapter(session)
        token_repo = TokenRepositoryAdapter(session)
        
        # 계정 조회
        account = await account_repo.get_by_email(email)
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # 토큰 조회
        token = await token_repo.get_by_account_id(account.id)
        
        status = {
            "account_id": str(account.id),
            "email": account.email,
            "display_name": account.display_name,
            "auth_type": account.auth_type.value,
            "status": account.status.value,
            "has_token": token is not None,
            "token_valid": token is not None and not token.is_expired(),
            "token_expires_at": token.expires_at.isoformat() if token else None,
        }
        
        logger.info(f"인증 상태 조회 완료: {email}, has_token={status['has_token']}")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"인증 상태 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
