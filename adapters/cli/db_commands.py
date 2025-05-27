"""
데이터베이스 관리 CLI 명령어

데이터베이스 초기화, 마이그레이션 등을 위한 CLI 명령어입니다.
"""

import asyncio
import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import text

from adapters.db.database import initialize_database
from config.adapters import get_config

# CLI 앱 생성
app = typer.Typer(name="db", help="데이터베이스 관리 명령어")
console = Console()


@app.command("init")
def init_database():
    """데이터베이스를 초기화합니다."""
    
    async def _init():
        try:
            console.print("[blue]데이터베이스 초기화 시작...[/blue]")
            
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            
            # 데이터베이스 초기화 (테이블 생성)
            await db_adapter.initialize()
            await db_adapter.create_tables()
            
            console.print("[green]✓ 데이터베이스 초기화가 완료되었습니다![/green]")
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_init())


@app.command("reset")
def reset_database():
    """데이터베이스를 리셋합니다. (모든 데이터 삭제)"""
    
    confirm = typer.confirm("모든 데이터가 삭제됩니다. 계속하시겠습니까?")
    if not confirm:
        console.print("[yellow]취소되었습니다.[/yellow]")
        return
    
    async def _reset():
        try:
            console.print("[blue]데이터베이스 리셋 시작...[/blue]")
            
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            
            # 데이터베이스 초기화 및 리셋 (테이블 삭제 후 재생성)
            await db_adapter.initialize()
            await db_adapter.reset()
            
            console.print("[green]✓ 데이터베이스 리셋이 완료되었습니다![/green]")
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_reset())


@app.command("tokens")
def show_tokens():
    """토큰 테이블의 내용을 조회합니다."""
    
    async def _show_tokens():
        try:
            console.print("[blue]토큰 테이블 조회 중...[/blue]")
            
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            await db_adapter.initialize()
            
            # 세션을 통해 토큰 조회
            async with db_adapter.get_session() as session:
                result = await session.execute(text("SELECT * FROM tokens"))
                tokens = result.fetchall()
                
                if not tokens:
                    console.print("[yellow]토큰 테이블이 비어있습니다.[/yellow]")
                    return
                
                # 테이블 생성
                table = Table(title="토큰 테이블")
                table.add_column("계정 ID", style="cyan")
                table.add_column("토큰 타입", style="green")
                table.add_column("Refresh Token", style="red")
                table.add_column("Scope", style="bright_blue")
                table.add_column("만료일", style="yellow")
                table.add_column("생성일", style="blue")
                table.add_column("업데이트일", style="magenta")
                
                for token in tokens:
                    # refresh_token이 있는지 확인 (암호화되어 있으므로 존재 여부만 표시)
                    has_refresh_token = "있음" if token.refresh_token else "없음"
                    # scope 정보 표시 (길면 줄임)
                    scope_display = token.scope[:50] + "..." if token.scope and len(token.scope) > 50 else (token.scope or "-")
                    table.add_row(
                        str(token.account_id)[:8] + "...",
                        token.token_type or "Bearer",
                        has_refresh_token,
                        scope_display,
                        str(token.expires_at) if token.expires_at else "-",
                        str(token.created_at) if token.created_at else "-",
                        str(token.updated_at) if token.updated_at else "-",
                    )
                
                console.print(table)
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_show_tokens())


@app.command("accounts")
def show_accounts():
    """계정 테이블의 내용을 조회합니다."""
    
    async def _show_accounts():
        try:
            console.print("[blue]계정 테이블 조회 중...[/blue]")
            
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            await db_adapter.initialize()
            
            # 세션을 통해 계정 조회
            async with db_adapter.get_session() as session:
                result = await session.execute(text("SELECT * FROM accounts"))
                accounts = result.fetchall()
                
                if not accounts:
                    console.print("[yellow]계정 테이블이 비어있습니다.[/yellow]")
                    return
                
                # 테이블 생성
                table = Table(title="계정 테이블")
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
                        account.auth_type,
                        account.status,
                        str(account.created_at) if account.created_at else "-",
                    )
                
                console.print(table)
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_show_accounts())


@app.command("auth-configs")
def show_auth_configs():
    """인증 설정 테이블들의 내용을 조회합니다."""
    
    async def _show_auth_configs():
        try:
            console.print("[blue]인증 설정 테이블 조회 중...[/blue]")
            
            # 설정 및 데이터베이스 초기화
            config = get_config()
            db_adapter = initialize_database(config)
            await db_adapter.initialize()
            
            # 세션을 통해 인증 설정 조회
            async with db_adapter.get_session() as session:
                # Authorization Code Configs 조회 (계정 정보와 JOIN)
                console.print("\n[bold]Authorization Code Configs:[/bold]")
                result = await session.execute(text("""
                    SELECT acc.account_id, acc.client_id, acc.redirect_uri, acc.tenant_id, acc.created_at, a.email
                    FROM auth_code_configs acc
                    JOIN accounts a ON acc.account_id = a.id
                """))
                auth_code_configs = result.fetchall()
                
                if not auth_code_configs:
                    console.print("[yellow]auth_code_configs 테이블이 비어있습니다.[/yellow]")
                else:
                    table = Table(title="Authorization Code Configs")
                    table.add_column("이메일", style="bright_green")
                    table.add_column("계정 ID", style="cyan")
                    table.add_column("Client ID", style="green")
                    table.add_column("Redirect URI", style="blue")
                    table.add_column("Tenant ID", style="magenta")
                    table.add_column("생성일", style="dim")
                    
                    for config in auth_code_configs:
                        table.add_row(
                            config.email,
                            str(config.account_id)[:8] + "...",
                            str(config.client_id)[:8] + "..." if config.client_id else "-",
                            config.redirect_uri or "-",
                            str(config.tenant_id)[:8] + "..." if config.tenant_id else "-",
                            str(config.created_at) if config.created_at else "-",
                        )
                    
                    console.print(table)
                
                # Device Code Configs 조회 (계정 정보와 JOIN)
                console.print("\n[bold]Device Code Configs:[/bold]")
                result = await session.execute(text("""
                    SELECT dcc.account_id, dcc.client_id, dcc.tenant_id, dcc.created_at, a.email
                    FROM device_code_configs dcc
                    JOIN accounts a ON dcc.account_id = a.id
                """))
                device_code_configs = result.fetchall()
                
                if not device_code_configs:
                    console.print("[yellow]device_code_configs 테이블이 비어있습니다.[/yellow]")
                else:
                    table = Table(title="Device Code Configs")
                    table.add_column("이메일", style="bright_green")
                    table.add_column("계정 ID", style="cyan")
                    table.add_column("Client ID", style="green")
                    table.add_column("Tenant ID", style="magenta")
                    table.add_column("생성일", style="dim")
                    
                    for config in device_code_configs:
                        table.add_row(
                            config.email,
                            str(config.account_id)[:8] + "...",
                            str(config.client_id)[:8] + "..." if config.client_id else "-",
                            str(config.tenant_id)[:8] + "..." if config.tenant_id else "-",
                            str(config.created_at) if config.created_at else "-",
                        )
                    
                    console.print(table)
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_show_auth_configs())


if __name__ == "__main__":
    app()
