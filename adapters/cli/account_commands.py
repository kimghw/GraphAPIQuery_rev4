"""
계정 관리 CLI 명령어

AccountManagementUseCase를 CLI 명령으로 노출하는 어댑터입니다.
"""

import asyncio
import json
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from core.domain.entities import AccountStatus, AuthType
from core.usecases.account_management import AccountManagementUseCase
from adapters.db.database import initialize_database
from adapters.db.repositories import AccountRepositoryAdapter, AuthConfigRepositoryAdapter
from adapters.logger import create_logger
from config.adapters import get_config

# CLI 앱 생성
app = typer.Typer(name="account", help="계정 관리 명령어")
console = Console()


@app.command("register")
def register_account(
    email: str = typer.Argument(..., help="Microsoft 365 이메일 주소"),
    auth_type: str = typer.Option("authorization_code", help="인증 타입 (authorization_code, device_code)"),
    display_name: Optional[str] = typer.Option(None, help="표시 이름"),
    client_id: Optional[str] = typer.Option(None, help="Azure 클라이언트 ID"),
    client_secret: Optional[str] = typer.Option(None, help="Azure 클라이언트 시크릿 (Authorization Code Flow만)"),
    redirect_uri: Optional[str] = typer.Option(None, help="리다이렉트 URI (Authorization Code Flow만)"),
    tenant_id: Optional[str] = typer.Option(None, help="Azure 테넌트 ID"),
):
    """새로운 Microsoft 365 계정을 등록합니다."""
    
    async def _register():
        try:
            # 인증 타입 검증
            try:
                auth_type_enum = AuthType(auth_type)
            except ValueError:
                console.print(f"[red]오류: 잘못된 인증 타입입니다. (authorization_code, device_code)[/red]")
                raise typer.Exit(1)
            
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            await db_adapter.initialize()
            
            # 세션 및 유즈케이스 생성
            async with db_adapter.get_session() as session:
                account_repo = AccountRepositoryAdapter(session)
                auth_config_repo = AuthConfigRepositoryAdapter(session)
                
                logger = create_logger("account_cli")
                usecase = AccountManagementUseCase(
                    account_repository=account_repo,
                    auth_config_repository=auth_config_repo,
                    logger=logger,
                )
                
                # 기본값 설정 (변수명 충돌 방지)
                final_client_id = client_id or config.get_azure_client_id()
                final_tenant_id = tenant_id or config.get_azure_tenant_id()
                final_client_secret = None
                final_redirect_uri = None
                
                if auth_type_enum == AuthType.AUTHORIZATION_CODE:
                    final_client_secret = client_secret or config.get_azure_client_secret()
                    final_redirect_uri = redirect_uri or config.get_oauth_redirect_uri()
                    
                    if not final_client_secret or not final_redirect_uri:
                        console.print("[red]오류: Authorization Code Flow에는 client_secret과 redirect_uri가 필요합니다.[/red]")
                        raise typer.Exit(1)
                
                # 계정 등록
                account = await usecase.register_account(
                    email=email,
                    auth_type=auth_type_enum,
                    display_name=display_name,
                    client_id=final_client_id,
                    client_secret=final_client_secret,
                    redirect_uri=final_redirect_uri,
                    tenant_id=final_tenant_id,
                )
                
                console.print(f"[green]✓ 계정이 성공적으로 등록되었습니다![/green]")
                console.print(f"계정 ID: {account.id}")
                console.print(f"이메일: {account.email}")
                console.print(f"인증 타입: {account.auth_type.value}")
                console.print(f"상태: {account.status.value}")
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_register())


@app.command("list")
def list_accounts(
    status: Optional[str] = typer.Option(None, help="상태별 필터 (active, inactive, error)"),
    auth_type: Optional[str] = typer.Option(None, help="인증 타입별 필터 (authorization_code, device_code)"),
    limit: int = typer.Option(10, help="조회할 계정 수"),
    skip: int = typer.Option(0, help="건너뛸 계정 수"),
):
    """등록된 계정 목록을 조회합니다."""
    
    async def _list():
        try:
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            await db_adapter.initialize()
            
            # 세션 및 유즈케이스 생성
            async with db_adapter.get_session() as session:
                account_repo = AccountRepositoryAdapter(session)
                auth_config_repo = AuthConfigRepositoryAdapter(session)
                
                logger = create_logger("account_cli")
                usecase = AccountManagementUseCase(
                    account_repository=account_repo,
                    auth_config_repository=auth_config_repo,
                    logger=logger,
                )
                
                # 필터 조건에 따른 조회
                if status:
                    try:
                        status_enum = AccountStatus(status)
                        accounts = await usecase.list_accounts_by_status(status_enum, skip, limit)
                    except ValueError:
                        console.print(f"[red]오류: 잘못된 상태입니다. (active, inactive, error)[/red]")
                        raise typer.Exit(1)
                elif auth_type:
                    try:
                        auth_type_enum = AuthType(auth_type)
                        accounts = await usecase.list_accounts_by_auth_type(auth_type_enum, skip, limit)
                    except ValueError:
                        console.print(f"[red]오류: 잘못된 인증 타입입니다. (authorization_code, device_code)[/red]")
                        raise typer.Exit(1)
                else:
                    accounts = await usecase.list_accounts(skip, limit)
                
                if not accounts:
                    console.print("[yellow]등록된 계정이 없습니다.[/yellow]")
                    return
                
                # 테이블 생성
                table = Table(title="등록된 계정 목록")
                table.add_column("ID", style="cyan")
                table.add_column("이메일", style="green")
                table.add_column("표시 이름", style="blue")
                table.add_column("인증 타입", style="magenta")
                table.add_column("상태", style="yellow")
                table.add_column("생성일", style="dim")
                
                for account in accounts:
                    table.add_row(
                        str(account.id)[:8] + "...",
                        account.email,
                        account.display_name or "-",
                        account.auth_type.value,
                        account.status.value,
                        account.created_at.strftime("%Y-%m-%d %H:%M") if account.created_at else "-",
                    )
                
                console.print(table)
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_list())


@app.command("get")
def get_account(
    account_id: Optional[str] = typer.Option(None, help="계정 ID"),
    email: Optional[str] = typer.Option(None, help="이메일 주소"),
):
    """특정 계정의 상세 정보를 조회합니다."""
    
    if not account_id and not email:
        console.print("[red]오류: account_id 또는 email 중 하나는 필수입니다.[/red]")
        raise typer.Exit(1)
    
    async def _get():
        try:
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            await db_adapter.initialize()
            
            # 세션 및 유즈케이스 생성
            async with db_adapter.get_session() as session:
                account_repo = AccountRepositoryAdapter(session)
                auth_config_repo = AuthConfigRepositoryAdapter(session)
                
                logger = create_logger("account_cli")
                usecase = AccountManagementUseCase(
                    account_repository=account_repo,
                    auth_config_repository=auth_config_repo,
                    logger=logger,
                )
                
                if account_id:
                    try:
                        account_uuid = UUID(account_id)
                        account = await usecase.get_account_by_id(account_uuid)
                    except ValueError:
                        console.print("[red]오류: 잘못된 계정 ID 형식입니다.[/red]")
                        raise typer.Exit(1)
                else:
                    account = await usecase.get_account_by_email(email)
                
                if not account:
                    console.print("[yellow]계정을 찾을 수 없습니다.[/yellow]")
                    return
                
                # 계정 정보 출력
                console.print(f"[bold]계정 정보[/bold]")
                console.print(f"ID: {account.id}")
                console.print(f"이메일: {account.email}")
                console.print(f"표시 이름: {account.display_name or '-'}")
                console.print(f"인증 타입: {account.auth_type.value}")
                console.print(f"상태: {account.status.value}")
                console.print(f"마지막 동기화: {account.last_sync_at or '-'}")
                console.print(f"생성일: {account.created_at}")
                console.print(f"수정일: {account.updated_at}")
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_get())


@app.command("delete")
def delete_account(
    account_id: Optional[str] = typer.Option(None, help="계정 ID"),
    email: Optional[str] = typer.Option(None, help="이메일 주소"),
    force: bool = typer.Option(False, "--force", "-f", help="확인 없이 강제 삭제"),
):
    """계정을 삭제합니다."""
    
    if not account_id and not email:
        console.print("[red]오류: account_id 또는 email 중 하나는 필수입니다.[/red]")
        raise typer.Exit(1)
    
    async def _delete():
        try:
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            await db_adapter.initialize()
            
            # 세션 및 유즈케이스 생성
            async with db_adapter.get_session() as session:
                account_repo = AccountRepositoryAdapter(session)
                auth_config_repo = AuthConfigRepositoryAdapter(session)
                
                logger = create_logger("account_cli")
                usecase = AccountManagementUseCase(
                    account_repository=account_repo,
                    auth_config_repository=auth_config_repo,
                    logger=logger,
                )
                
                # 계정 조회
                if account_id:
                    try:
                        account_uuid = UUID(account_id)
                        account = await usecase.get_account_by_id(account_uuid)
                    except ValueError:
                        console.print("[red]오류: 잘못된 계정 ID 형식입니다.[/red]")
                        raise typer.Exit(1)
                else:
                    account = await usecase.get_account_by_email(email)
                
                if not account:
                    console.print("[yellow]계정을 찾을 수 없습니다.[/yellow]")
                    return
                
                # 삭제 확인
                if not force:
                    console.print(f"[yellow]다음 계정을 삭제하시겠습니까?[/yellow]")
                    console.print(f"ID: {account.id}")
                    console.print(f"이메일: {account.email}")
                    console.print(f"표시 이름: {account.display_name or '-'}")
                    
                    confirm = typer.confirm("정말로 삭제하시겠습니까?")
                    if not confirm:
                        console.print("[yellow]삭제가 취소되었습니다.[/yellow]")
                        return
                
                # 계정 삭제
                success = await usecase.delete_account(account.id)
                
                if success:
                    console.print(f"[green]✓ 계정이 성공적으로 삭제되었습니다![/green]")
                    console.print(f"삭제된 계정: {account.email}")
                else:
                    console.print(f"[red]계정 삭제에 실패했습니다.[/red]")
                    raise typer.Exit(1)
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_delete())


@app.command("update")
def update_account(
    account_id: Optional[str] = typer.Option(None, help="계정 ID"),
    email: Optional[str] = typer.Option(None, help="이메일 주소"),
    display_name: Optional[str] = typer.Option(None, help="새로운 표시 이름"),
    auth_type: Optional[str] = typer.Option(None, help="새로운 인증 타입 (authorization_code, device_code)"),
    tenant_id: Optional[str] = typer.Option(None, help="새로운 테넌트 ID"),
):
    """계정 정보를 업데이트합니다."""
    
    if not account_id and not email:
        console.print("[red]오류: account_id 또는 email 중 하나는 필수입니다.[/red]")
        raise typer.Exit(1)
    
    if not any([display_name, auth_type, tenant_id]):
        console.print("[red]오류: 업데이트할 정보를 하나 이상 입력해주세요.[/red]")
        raise typer.Exit(1)
    
    async def _update():
        try:
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            await db_adapter.initialize()
            
            # 세션 및 유즈케이스 생성
            async with db_adapter.get_session() as session:
                account_repo = AccountRepositoryAdapter(session)
                auth_config_repo = AuthConfigRepositoryAdapter(session)
                
                logger = create_logger("account_cli")
                usecase = AccountManagementUseCase(
                    account_repository=account_repo,
                    auth_config_repository=auth_config_repo,
                    logger=logger,
                )
                
                # 계정 조회
                if account_id:
                    try:
                        account_uuid = UUID(account_id)
                        account = await usecase.get_account_by_id(account_uuid)
                    except ValueError:
                        console.print("[red]오류: 잘못된 계정 ID 형식입니다.[/red]")
                        raise typer.Exit(1)
                else:
                    account = await usecase.get_account_by_email(email)
                
                if not account:
                    console.print("[yellow]계정을 찾을 수 없습니다.[/yellow]")
                    return
                
                # 인증 타입 검증
                auth_type_enum = None
                if auth_type:
                    try:
                        auth_type_enum = AuthType(auth_type)
                    except ValueError:
                        console.print(f"[red]오류: 잘못된 인증 타입입니다. (authorization_code, device_code)[/red]")
                        raise typer.Exit(1)
                
                # 업데이트 전 정보 출력
                console.print(f"[yellow]업데이트할 계정:[/yellow]")
                console.print(f"ID: {account.id}")
                console.print(f"이메일: {account.email}")
                console.print(f"현재 표시 이름: {account.display_name or '-'}")
                console.print(f"현재 인증 타입: {account.auth_type.value}")
                console.print(f"현재 테넌트 ID: {account.tenant_id or '-'}")
                console.print()
                
                # 계정 업데이트
                updated_account = await usecase.update_account(
                    account_id=account.id,
                    display_name=display_name,
                    auth_type=auth_type_enum,
                    tenant_id=tenant_id,
                )
                
                if updated_account:
                    console.print(f"[green]✓ 계정이 성공적으로 업데이트되었습니다![/green]")
                    console.print(f"업데이트된 표시 이름: {updated_account.display_name or '-'}")
                    console.print(f"업데이트된 인증 타입: {updated_account.auth_type.value}")
                    console.print(f"업데이트된 테넌트 ID: {updated_account.tenant_id or '-'}")
                else:
                    console.print(f"[red]계정 업데이트에 실패했습니다.[/red]")
                    raise typer.Exit(1)
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_update())


if __name__ == "__main__":
    app()
