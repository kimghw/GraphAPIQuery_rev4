"""
인증 관련 CLI 명령어

Microsoft 365 OAuth 2.0 인증 플로우를 처리하는 CLI 명령어들입니다.
"""

import asyncio
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from core.domain.entities import AuthType
from adapters.db.database import initialize_database
from adapters.db.repositories import AccountRepositoryAdapter, AuthConfigRepositoryAdapter
from adapters.logger import create_logger
from config.adapters import get_config

console = Console()
auth_app = typer.Typer(help="인증 관련 명령어")


@auth_app.command("start-auth-code")
def start_authorization_code_flow(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
    scope: str = typer.Option(
        "https://graph.microsoft.com/.default",
        "--scope", "-s",
        help="요청할 권한 범위"
    ),
):
    """Authorization Code Flow 인증을 시작합니다."""
    asyncio.run(_start_authorization_code_flow(email, scope))


@auth_app.command("complete-auth-code")
def complete_authorization_code_flow(
    code: str = typer.Option(..., "--code", "-c", help="인증 코드"),
    state: str = typer.Option(..., "--state", "-s", help="State 값"),
    scope: str = typer.Option(
        "https://graph.microsoft.com/.default",
        "--scope",
        help="권한 범위"
    ),
):
    """Authorization Code Flow 인증을 완료합니다."""
    asyncio.run(_complete_authorization_code_flow(code, state, scope))


@auth_app.command("start-device-code")
def start_device_code_flow(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
    scope: str = typer.Option(
        "https://graph.microsoft.com/.default",
        "--scope", "-s",
        help="요청할 권한 범위"
    ),
):
    """Device Code Flow 인증을 시작합니다."""
    asyncio.run(_start_device_code_flow(email, scope))


@auth_app.command("poll-device-code")
def poll_device_code_flow(
    device_code: str = typer.Option(..., "--device-code", "-d", help="디바이스 코드"),
    scope: str = typer.Option(
        "https://graph.microsoft.com/.default",
        "--scope",
        help="권한 범위"
    ),
    max_attempts: int = typer.Option(60, "--max-attempts", help="최대 시도 횟수"),
    interval: int = typer.Option(5, "--interval", help="폴링 간격 (초)"),
):
    """Device Code Flow 인증을 폴링합니다."""
    asyncio.run(_poll_device_code_flow(device_code, scope, max_attempts, interval))


@auth_app.command("refresh-token")
def refresh_token(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
):
    """토큰을 갱신합니다."""
    asyncio.run(_refresh_token(email))


@auth_app.command("revoke-token")
def revoke_token(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
    force: bool = typer.Option(False, "--force", "-f", help="확인 없이 강제 실행"),
):
    """토큰을 폐기합니다."""
    asyncio.run(_revoke_token(email, force))


@auth_app.command("get-profile")
def get_user_profile(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
):
    """사용자 프로필을 조회합니다."""
    asyncio.run(_get_user_profile(email))


@auth_app.command("check-tokens")
def check_expiring_tokens(
    minutes: int = typer.Option(5, "--minutes", "-m", help="만료 임박 기준 시간 (분)"),
):
    """곧 만료될 토큰들을 확인하고 갱신합니다."""
    asyncio.run(_check_expiring_tokens(minutes))


@auth_app.command("get-config")
def get_auth_config(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
):
    """계정의 인증 설정을 조회합니다."""
    asyncio.run(_get_auth_config(email))


async def _start_authorization_code_flow(email: str, scope: str):
    """Authorization Code Flow 인증 시작"""
    try:
        factory = get_adapter_factory()
        
        db_adapter = factory.get_database_adapter()
        
        async with db_adapter.get_session() as session:
            # 계정 조회
            account_usecase = factory.create_account_management_usecase(session)
            account = await account_usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            if account.auth_type != AuthType.AUTHORIZATION_CODE:
                console.print(f"[red]Authorization Code Flow가 아닙니다: {account.auth_type}[/red]")
                return
            
            # 인증 시작
            auth_usecase = factory.create_authentication_usecase(session)
            authorization_url, state = await auth_usecase.start_authorization_code_flow(
                account.id, scope
            )
            
            # 결과 출력
            console.print(Panel.fit(
                f"[bold green]Authorization Code Flow 시작됨[/bold green]\n\n"
                f"[bold]계정:[/bold] {email}\n"
                f"[bold]State:[/bold] {state}\n\n"
                f"[bold]다음 URL로 이동하여 인증을 완료하세요:[/bold]\n"
                f"[link]{authorization_url}[/link]\n\n"
                f"[yellow]인증 완료 후 받은 코드로 다음 명령어를 실행하세요:[/yellow]\n"
                f"[cyan]python main.py auth complete-auth-code --code <CODE> --state {state}[/cyan]",
                title="🔐 Authorization Code Flow"
            ))
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _complete_authorization_code_flow(code: str, state: str, scope: str):
    """Authorization Code Flow 인증 완료"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        
        async with db_adapter.get_session() as session:
            auth_usecase = factory.create_authentication_usecase(session)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("토큰 교환 중...", total=None)
                
                token = await auth_usecase.complete_authorization_code_flow(
                    code, state, scope
                )
                
                progress.update(task, description="완료!")
            
            console.print(Panel.fit(
                f"[bold green]인증 완료![/bold green]\n\n"
                f"[bold]계정 ID:[/bold] {token.account_id}\n"
                f"[bold]토큰 타입:[/bold] {token.token_type}\n"
                f"[bold]만료 시간:[/bold] {token.expires_at}\n"
                f"[bold]권한 범위:[/bold] {token.scope}",
                title="✅ 인증 성공"
            ))
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _start_device_code_flow(email: str, scope: str):
    """Device Code Flow 인증 시작"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        
        async with db_adapter.get_session() as session:
            # 계정 조회
            account_usecase = factory.create_account_management_usecase(session)
            account = await account_usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            if account.auth_type != AuthType.DEVICE_CODE:
                console.print(f"[red]Device Code Flow가 아닙니다: {account.auth_type}[/red]")
                return
            
            # 인증 시작
            auth_usecase = factory.create_authentication_usecase(session)
            device_code_info = await auth_usecase.start_device_code_flow(
                account.id, scope
            )
            
            # 결과 출력
            console.print(Panel.fit(
                f"[bold green]Device Code Flow 시작됨[/bold green]\n\n"
                f"[bold]계정:[/bold] {email}\n"
                f"[bold]사용자 코드:[/bold] [yellow]{device_code_info['user_code']}[/yellow]\n"
                f"[bold]디바이스 코드:[/bold] {device_code_info['device_code']}\n\n"
                f"[bold]다음 URL로 이동하여 사용자 코드를 입력하세요:[/bold]\n"
                f"[link]{device_code_info['verification_uri']}[/link]\n\n"
                f"[yellow]인증 완료를 기다리려면 다음 명령어를 실행하세요:[/yellow]\n"
                f"[cyan]python main.py auth poll-device-code --device-code {device_code_info['device_code']}[/cyan]",
                title="📱 Device Code Flow"
            ))
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _poll_device_code_flow(device_code: str, scope: str, max_attempts: int, interval: int):
    """Device Code Flow 폴링"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        
        async with db_adapter.get_session() as session:
            auth_usecase = factory.create_authentication_usecase(session)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("인증 대기 중...", total=max_attempts)
                
                try:
                    token = await auth_usecase.poll_device_code_flow(
                        device_code, scope, max_attempts, interval
                    )
                    
                    progress.update(task, description="완료!", completed=max_attempts)
                    
                    console.print(Panel.fit(
                        f"[bold green]인증 완료![/bold green]\n\n"
                        f"[bold]계정 ID:[/bold] {token.account_id}\n"
                        f"[bold]토큰 타입:[/bold] {token.token_type}\n"
                        f"[bold]만료 시간:[/bold] {token.expires_at}\n"
                        f"[bold]권한 범위:[/bold] {token.scope}",
                        title="✅ 인증 성공"
                    ))
                    
                except TimeoutError:
                    console.print("[red]인증 시간이 초과되었습니다.[/red]")
                except Exception as e:
                    if "access_denied" in str(e):
                        console.print("[red]사용자가 인증을 거부했습니다.[/red]")
                    elif "expired_token" in str(e):
                        console.print("[red]디바이스 코드가 만료되었습니다.[/red]")
                    else:
                        raise
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _refresh_token(email: str):
    """토큰 갱신"""
    try:
        factory = get_adapter_factory()
        
        db_adapter = factory.get_database_adapter()
        
        async with db_adapter.get_session() as session:
            # 계정 조회
            account_usecase = factory.create_account_management_usecase(session)
            account = await account_usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 토큰 갱신
            auth_usecase = factory.create_authentication_usecase(session)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("토큰 갱신 중...", total=None)
                
                token = await auth_usecase.refresh_token(account.id)
                
                progress.update(task, description="완료!")
            
            if token:
                console.print(Panel.fit(
                    f"[bold green]토큰 갱신 완료![/bold green]\n\n"
                    f"[bold]계정:[/bold] {email}\n"
                    f"[bold]토큰 타입:[/bold] {token.token_type}\n"
                    f"[bold]만료 시간:[/bold] {token.expires_at}\n"
                    f"[bold]권한 범위:[/bold] {token.scope}",
                    title="🔄 토큰 갱신"
                ))
            else:
                console.print("[red]토큰 갱신에 실패했습니다.[/red]")
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _revoke_token(email: str, force: bool):
    """토큰 폐기"""
    try:
        if not force:
            if not Confirm.ask(f"정말로 {email} 계정의 토큰을 폐기하시겠습니까?"):
                console.print("[yellow]취소되었습니다.[/yellow]")
                return
        
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        
        async with db_adapter.get_session() as session:
            # 계정 조회
            account_usecase = factory.create_account_management_usecase(session)
            account = await account_usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 토큰 폐기
            auth_usecase = factory.create_authentication_usecase(session)
            success = await auth_usecase.revoke_token(account.id)
            
            if success:
                console.print(f"[green]토큰이 성공적으로 폐기되었습니다: {email}[/green]")
            else:
                console.print(f"[red]토큰 폐기에 실패했습니다: {email}[/red]")
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _get_user_profile(email: str):
    """사용자 프로필 조회"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        
        async with db_adapter.get_session() as session:
            # 계정 조회
            account_usecase = factory.create_account_management_usecase(session)
            account = await account_usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 프로필 조회
            auth_usecase = factory.create_authentication_usecase(session)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("프로필 조회 중...", total=None)
                
                profile = await auth_usecase.get_user_profile(account.id)
                
                progress.update(task, description="완료!")
            
            if profile:
                table = Table(title=f"👤 사용자 프로필: {email}")
                table.add_column("속성", style="cyan")
                table.add_column("값", style="white")
                
                # 주요 프로필 정보 표시
                profile_fields = [
                    ("ID", profile.get("id")),
                    ("사용자 주체 이름", profile.get("userPrincipalName")),
                    ("표시 이름", profile.get("displayName")),
                    ("이메일", profile.get("mail")),
                    ("직책", profile.get("jobTitle")),
                    ("부서", profile.get("department")),
                    ("회사", profile.get("companyName")),
                    ("사무실 위치", profile.get("officeLocation")),
                    ("전화번호", profile.get("businessPhones")),
                    ("모바일", profile.get("mobilePhone")),
                ]
                
                for field_name, field_value in profile_fields:
                    if field_value:
                        if isinstance(field_value, list):
                            field_value = ", ".join(field_value)
                        table.add_row(field_name, str(field_value))
                
                console.print(table)
            else:
                console.print("[red]프로필 조회에 실패했습니다.[/red]")
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _check_expiring_tokens(minutes: int):
    """만료 임박 토큰 확인 및 갱신"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        
        async with db_adapter.get_session() as session:
            auth_usecase = factory.create_authentication_usecase(session)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("토큰 확인 중...", total=None)
                
                refreshed_count = await auth_usecase.check_and_refresh_expiring_tokens(minutes)
                
                progress.update(task, description="완료!")
            
            console.print(f"[green]{refreshed_count}개의 토큰이 갱신되었습니다.[/green]")
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _get_auth_config(email: str):
    """인증 설정 조회"""
    try:
        # 설정 및 데이터베이스 초기화
        config = get_config()
        db_adapter = initialize_database(config)
        await db_adapter.initialize()
        
        # 세션 및 유즈케이스 생성
        async with db_adapter.get_session() as session:
            account_repo = AccountRepositoryAdapter(session)
            auth_config_repo = AuthConfigRepositoryAdapter(session)
            
            logger = create_logger("auth_cli")
            from core.usecases.account_management import AccountManagementUseCase
            usecase = AccountManagementUseCase(
                account_repository=account_repo,
                auth_config_repository=auth_config_repo,
                logger=logger,
            )
            
            # 계정 조회
            account = await usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 인증 설정 조회
            auth_config = await usecase.get_auth_config(account.id)
            
            if not auth_config:
                console.print(f"[red]인증 설정을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 결과 출력
            table = Table(title=f"🔐 인증 설정: {email}")
            table.add_column("속성", style="cyan")
            table.add_column("값", style="white")
            
            table.add_row("계정 ID", str(account.id))
            table.add_row("이메일", account.email)
            table.add_row("인증 타입", account.auth_type.value)
            
            if account.auth_type == AuthType.AUTHORIZATION_CODE:
                table.add_row("Client ID", auth_config.client_id)
                table.add_row("Tenant ID", auth_config.tenant_id)
                table.add_row("Redirect URI", auth_config.redirect_uri)
                table.add_row("Client Secret", "***" + auth_config.client_secret[-4:] if auth_config.client_secret else "없음")
            elif account.auth_type == AuthType.DEVICE_CODE:
                table.add_row("Client ID", auth_config.client_id)
                table.add_row("Tenant ID", auth_config.tenant_id)
            
            console.print(table)
        
        await db_adapter.close()
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")
