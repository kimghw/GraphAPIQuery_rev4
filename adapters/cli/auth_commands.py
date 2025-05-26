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
from adapters.factory import get_adapter_factory
from adapters.logger import create_logger
from config.adapters import get_config

console = Console()
auth_app = typer.Typer(help="인증 관련 명령어")


@auth_app.command("start-auth-code")
def start_authorization_code_flow(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
    scope: str = typer.Option(
        "https://graph.microsoft.com/.default offline_access",
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
        "https://graph.microsoft.com/.default offline_access",
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
        "https://graph.microsoft.com/.default offline_access",
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
        "https://graph.microsoft.com/.default offline_access",
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


@auth_app.command("token-status")
def get_token_status(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
):
    """토큰 상태를 상세히 조회합니다."""
    asyncio.run(_get_token_status(email))


@auth_app.command("validate-token")
def validate_token_integrity(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
):
    """토큰의 무결성을 검증합니다."""
    asyncio.run(_validate_token_integrity(email))


async def _start_authorization_code_flow(email: str, scope: str):
    """Authorization Code Flow 인증 시작"""
    try:
        factory = get_adapter_factory()
        
        db_adapter = factory.get_database_adapter()
        await db_adapter.initialize()
        
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
            console.print(f"[bold green]✅ Authorization Code Flow 시작됨[/bold green]")
            console.print(f"[bold]계정:[/bold] {email}")
            console.print(f"[bold]State:[/bold] {state}")
            console.print()
            console.print(f"[bold]다음 URL로 이동하여 인증을 완료하세요:[/bold]")
            console.print(f"[link]{authorization_url}[/link]")
            console.print()
            console.print(f"[yellow]인증 완료 후 받은 코드로 다음 명령어를 실행하세요:[/yellow]")
            console.print(f"[cyan]python main.py auth complete-auth-code --code <CODE> --state {state}[/cyan]")
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _get_token_status(email: str):
    """토큰 상태 상세 조회"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        await db_adapter.initialize()
        
        async with db_adapter.get_session() as session:
            # 계정 조회
            account_usecase = factory.create_account_management_usecase(session)
            account = await account_usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 토큰 상태 조회
            auth_usecase = factory.create_authentication_usecase(session)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("토큰 상태 조회 중...", total=None)
                
                status = await auth_usecase.get_token_status(account.id)
                
                progress.update(task, description="완료!")
            
            if not status:
                console.print(f"[red]토큰을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 기본 정보 테이블
            basic_table = Table(title=f"🔑 토큰 기본 정보: {email}")
            basic_table.add_column("속성", style="cyan")
            basic_table.add_column("값", style="white")
            
            basic_table.add_row("계정 ID", status["account_id"])
            basic_table.add_row("토큰 타입", status["token_type"])
            basic_table.add_row("권한 범위", status["scope"])
            basic_table.add_row("생성 시간", status["created_at"])
            basic_table.add_row("수정 시간", status["updated_at"])
            basic_table.add_row("암호화 여부", "✅ 예" if status["is_encrypted"] else "❌ 아니오")
            basic_table.add_row("갱신 가능", "✅ 예" if status["can_refresh"] else "❌ 아니오")
            
            console.print(basic_table)
            
            # 만료 정보 테이블
            expiry_table = Table(title="⏰ 만료 정보")
            expiry_table.add_column("구분", style="cyan")
            expiry_table.add_column("만료 시간", style="white")
            expiry_table.add_column("상태", style="white")
            
            # DB 만료 정보
            db_status = "❌ 만료됨" if status["db_is_expired"] else "✅ 유효함"
            if not status["db_is_expired"] and status["db_is_near_expiry"]:
                db_status = "⚠️ 곧 만료"
            
            expiry_table.add_row("DB 기준", status["db_expires_at"], db_status)
            
            # JWT 만료 정보 (있는 경우)
            if status.get("jwt_expires_at"):
                jwt_status = "❌ 만료됨" if status["jwt_is_expired"] else "✅ 유효함"
                expiry_table.add_row("JWT 기준", status["jwt_expires_at"], jwt_status)
                
                # 시간 차이 정보
                time_diff = status.get("expiry_time_diff_seconds", 0)
                match_status = "✅ 일치" if status.get("expiry_times_match", False) else f"❌ 차이: {time_diff:.0f}초"
                expiry_table.add_row("시간 일치성", "-", match_status)
            
            console.print(expiry_table)
            
            # JWT 페이로드 정보 (있는 경우)
            if status.get("jwt_payload"):
                jwt_table = Table(title="🎫 JWT 페이로드 정보")
                jwt_table.add_column("속성", style="cyan")
                jwt_table.add_column("값", style="white")
                
                payload = status["jwt_payload"]
                jwt_fields = [
                    ("발급자 (iss)", payload.get("iss")),
                    ("대상 (aud)", payload.get("aud")),
                    ("사용자 ID (sub)", payload.get("sub")),
                    ("앱 ID (appid)", payload.get("appid")),
                    ("테넌트 ID (tid)", payload.get("tid")),
                    ("사용자명 (upn)", payload.get("upn")),
                    ("이름 (name)", payload.get("name")),
                    ("권한 (scp)", payload.get("scp")),
                ]
                
                for field_name, field_value in jwt_fields:
                    if field_value:
                        jwt_table.add_row(field_name, str(field_value))
                
                console.print(jwt_table)
            
            # 오류 정보 (있는 경우)
            if status.get("decryption_error"):
                console.print(Panel.fit(
                    f"[red]복호화 오류:[/red] {status['decryption_error']}",
                    title="⚠️ 오류"
                ))
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _validate_token_integrity(email: str):
    """토큰 무결성 검증"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        await db_adapter.initialize()
        
        async with db_adapter.get_session() as session:
            # 계정 조회
            account_usecase = factory.create_account_management_usecase(session)
            account = await account_usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 토큰 무결성 검증
            auth_usecase = factory.create_authentication_usecase(session)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("토큰 무결성 검증 중...", total=None)
                
                result = await auth_usecase.validate_token_integrity(account.id)
                
                progress.update(task, description="완료!")
            
            # 검증 결과 테이블
            table = Table(title=f"🔍 토큰 무결성 검증: {email}")
            table.add_column("검증 항목", style="cyan")
            table.add_column("결과", style="white")
            table.add_column("상태", style="white")
            
            checks = [
                ("토큰 존재", result["token_exists"], "토큰이 데이터베이스에 존재하는지 확인"),
                ("암호화 여부", result["is_encrypted"], "토큰이 암호화되어 있는지 확인"),
                ("복호화 성공", result["decryption_success"], "토큰을 성공적으로 복호화할 수 있는지 확인"),
                ("유효한 JWT", result["is_valid_jwt"], "JWT 형식이 올바른지 확인"),
                ("만료시간 일관성", result["expiry_times_consistent"], "DB와 JWT 만료시간이 일치하는지 확인"),
                ("토큰 유효성", result["token_not_expired"], "토큰이 만료되지 않았는지 확인"),
            ]
            
            for check_name, check_result, description in checks:
                status_icon = "✅" if check_result else "❌"
                result_text = "통과" if check_result else "실패"
                table.add_row(check_name, f"{status_icon} {result_text}", description)
            
            console.print(table)
            
            # 전체 결과
            overall_status = result["overall_valid"]
            if overall_status:
                console.print(Panel.fit(
                    "[bold green]✅ 토큰이 유효하고 무결성에 문제가 없습니다.[/bold green]",
                    title="검증 결과"
                ))
            else:
                console.print(Panel.fit(
                    "[bold red]❌ 토큰에 문제가 있습니다. 새로 인증하는 것을 권장합니다.[/bold red]",
                    title="검증 결과"
                ))
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _complete_authorization_code_flow(code: str, state: str, scope: str):
    """Authorization Code Flow 인증 완료"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        await db_adapter.initialize()
        
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
        await db_adapter.initialize()
        
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
        await db_adapter.initialize()
        
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
        await db_adapter.initialize()
        
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
        await db_adapter.initialize()
        
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
        await db_adapter.initialize()
        
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
        await db_adapter.initialize()
        
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
        # 설정 및 데이터

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



@auth_app.command("show-raw-token")
def show_raw_token(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
    show_encrypted: bool = typer.Option(False, "--show-encrypted", help="암호화된 토큰도 표시"),
):
    """토큰의 원본 값을 표시합니다."""
    asyncio.run(_show_raw_token(email, show_encrypted))


@auth_app.command("log-raw-token")
def log_raw_token(
    email: str = typer.Option(..., "--email", "-e", help="계정 이메일"),
):
    """토큰의 원본 값을 로그로 출력합니다."""
    asyncio.run(_log_raw_token(email))


async def _show_raw_token(email: str, show_encrypted: bool):
    """토큰 원본 값 표시"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        await db_adapter.initialize()
        
        async with db_adapter.get_session() as session:
            # 계정 조회
            account_usecase = factory.create_account_management_usecase(session)
            account = await account_usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 토큰 조회
            auth_usecase = factory.create_authentication_usecase(session)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("토큰 조회 중...", total=None)
                
                # 토큰 리포지토리에서 직접 조회
                token_repo = factory.create_token_repository(session)
                token_record = await token_repo.get_by_account_id(account.id)
                
                progress.update(task, description="완료!")
            
            if not token_record:
                console.print(f"[red]토큰을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 암호화된 토큰 표시 (옵션)
            if show_encrypted:
                console.print(Panel.fit(
                    f"[bold yellow]암호화된 토큰 (DB 저장값):[/bold yellow]\n\n"
                    f"[dim]{token_record.encrypted_access_token}[/dim]",
                    title="🔒 암호화된 토큰"
                ))
                console.print()
            
            # 복호화된 토큰 표시
            try:
                # 암호화 서비스를 통해 복호화
                encryption_service = factory.get_encryption_service()
                decrypted_token = await encryption_service.decrypt(token_record.encrypted_access_token)
                
                console.print(Panel.fit(
                    f"[bold green]복호화된 액세스 토큰:[/bold green]\n\n"
                    f"[white]{decrypted_token}[/white]",
                    title="🔓 원본 액세스 토큰"
                ))
                
                # 리프레시 토큰이 있는 경우
                if token_record.encrypted_refresh_token:
                    decrypted_refresh_token = await encryption_service.decrypt(token_record.encrypted_refresh_token)
                    console.print()
                    console.print(Panel.fit(
                        f"[bold blue]복호화된 리프레시 토큰:[/bold blue]\n\n"
                        f"[white]{decrypted_refresh_token}[/white]",
                        title="🔄 원본 리프레시 토큰"
                    ))
                
                # JWT 디코딩 시도
                try:
                    import jwt
                    import json
                    
                    # JWT 헤더와 페이로드 디코딩 (서명 검증 없이)
                    decoded_token = jwt.decode(decrypted_token, options={"verify_signature": False})
                    
                    console.print()
                    console.print(Panel.fit(
                        f"[bold cyan]JWT 페이로드 (디코딩됨):[/bold cyan]\n\n"
                        f"[white]{json.dumps(decoded_token, indent=2, ensure_ascii=False)}[/white]",
                        title="�� JWT 페이로드"
                    ))
                    
                except Exception as jwt_error:
                    console.print()
                    console.print(Panel.fit(
                        f"[yellow]JWT 디코딩 실패: {str(jwt_error)}[/yellow]",
                        title="⚠️ JWT 디코딩 오류"
                    ))
                
            except Exception as decrypt_error:
                console.print(Panel.fit(
                    f"[red]토큰 복호화 실패: {str(decrypt_error)}[/red]",
                    title="❌ 복호화 오류"
                ))
            
            # 토큰 메타데이터 표시
            console.print()
            metadata_table = Table(title="📊 토큰 메타데이터")
            metadata_table.add_column("속성", style="cyan")
            metadata_table.add_column("값", style="white")
            
            metadata_table.add_row("토큰 ID", str(token_record.id))
            metadata_table.add_row("계정 ID", str(token_record.account_id))
            metadata_table.add_row("토큰 타입", token_record.token_type)
            metadata_table.add_row("권한 범위", token_record.scope or "없음")
            metadata_table.add_row("만료 시간", str(token_record.expires_at))
            metadata_table.add_row("생성 시간", str(token_record.created_at))
            metadata_table.add_row("수정 시간", str(token_record.updated_at))
            metadata_table.add_row("리프레시 토큰 존재", "✅ 예" if token_record.encrypted_refresh_token else "❌ 아니오")
            
            console.print(metadata_table)
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")


async def _log_raw_token(email: str):
    """토큰 원본 값을 로그로 출력"""
    try:
        factory = get_adapter_factory()
        db_adapter = factory.get_database_adapter()
        await db_adapter.initialize()
        
        async with db_adapter.get_session() as session:
            # 계정 조회
            account_usecase = factory.create_account_management_usecase(session)
            account = await account_usecase.get_account_by_email(email)
            
            if not account:
                console.print(f"[red]계정을 찾을 수 없습니다: {email}[/red]")
                return
            
            # 인증 유즈케이스의 log_raw_token_values 메서드 호출
            auth_usecase = factory.create_authentication_usecase(session)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("토큰 원본 값 로그 출력 중...", total=None)
                
                result = await auth_usecase.log_raw_token_values(account.id)
                
                progress.update(task, description="완료!")
            
            if "error" in result:
                console.print(f"[red]오류: {result['error']}[/red]")
                return
            
            # 결과 요약 표시
            console.print(Panel.fit(
                f"[bold green]토큰 원본 값이 로그에 출력되었습니다![/bold green]\n\n"
                f"[bold]계정 ID:[/bold] {result['account_id']}\n"
                f"[bold]토큰 타입:[/bold] {result['token_type']}\n"
                f"[bold]권한 범위:[/bold] {result['scope']}\n"
                f"[bold]생성 시간:[/bold] {result['created_at']}\n"
                f"[bold]만료 시간:[/bold] {result['expires_at']}\n\n"
                f"[yellow]상세한 토큰 정보는 로그를 확인하세요.[/yellow]\n"
                f"[dim]로그에서 '[토큰 원본]' 태그로 검색하면 관련 정보를 찾을 수 있습니다.[/dim]",
                title="📝 토큰 로그 출력 완료"
            ))
            
            # 추가 정보가 있는 경우 표시
            if result.get("jwt_header") or result.get("jwt_payload"):
                console.print()
                console.print("[cyan]JWT 토큰 정보가 로그에 포함되었습니다:[/cyan]")
                
                if result.get("jwt_header"):
                    console.print("  • JWT Header 정보")
                if result.get("jwt_payload"):
                    console.print("  • JWT Payload 정보")
                    console.print("  • 만료 시간 비교 정보")
            
            if result.get("jwt_parse_error"):
                console.print()
                console.print(f"[yellow]JWT 파싱 중 오류 발생: {result['jwt_parse_error']}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]오류 발생: {str(e)}[/red]")
