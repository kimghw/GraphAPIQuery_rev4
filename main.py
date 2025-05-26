"""
Microsoft 365 Graph API 메일 처리 시스템

메인 진입점 파일입니다.
"""

import asyncio
import typer
from rich.console import Console

from adapters.cli.account_commands import app as account_app
from adapters.cli.auth_commands import auth_app
from adapters.cli.db_commands import app as db_app
from adapters.db.database import initialize_database
from config.adapters import get_config

# 메인 CLI 앱
app = typer.Typer(
    name="graphapi",
    help="Microsoft 365 Graph API 메일 처리 시스템",
    no_args_is_help=True,
)

# 서브 명령어 추가
app.add_typer(account_app, name="account")
app.add_typer(auth_app, name="auth")
app.add_typer(db_app, name="db")

console = Console()


@app.command("init-db")
def init_database(
    drop_existing: bool = typer.Option(False, "--drop", help="기존 테이블을 삭제하고 재생성"),
):
    """데이터베이스를 초기화합니다."""
    
    async def _init_db():
        try:
            config = get_config()
            console.print(f"[blue]환경: {config.get_environment()}[/blue]")
            console.print(f"[blue]데이터베이스: {config.get_database_url()}[/blue]")
            
            # 데이터베이스 어댑터 초기화
            db_adapter = initialize_database(config)
            await db_adapter.initialize()
            
            if drop_existing:
                console.print("[yellow]기존 테이블을 삭제하는 중...[/yellow]")
                await db_adapter.drop_tables()
            
            console.print("[blue]데이터베이스 테이블을 생성하는 중...[/blue]")
            await db_adapter.create_tables()
            
            console.print("[green]✓ 데이터베이스가 성공적으로 초기화되었습니다![/green]")
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_init_db())


@app.command("version")
def show_version():
    """버전 정보를 표시합니다."""
    console.print("[bold]Microsoft 365 Graph API 메일 처리 시스템[/bold]")
    console.print("버전: 1.0.0")
    console.print("작성자: GraphAPI Team")


@app.command("config")
def show_config():
    """현재 설정을 표시합니다."""
    try:
        config = get_config()
        
        console.print("[bold]현재 설정[/bold]")
        console.print(f"환경: {config.get_environment()}")
        console.print(f"디버그 모드: {config.is_debug()}")
        console.print(f"데이터베이스 URL: {config.get_database_url()}")
        console.print(f"Redis URL: {config.get_redis_url()}")
        console.print(f"Azure 테넌트 ID: {config.get_azure_tenant_id()}")
        console.print(f"OAuth 리다이렉트 URI: {config.get_oauth_redirect_uri()}")
        console.print(f"API 호스트: {config.get_api_host()}")
        console.print(f"API 포트: {config.get_api_port()}")
        console.print(f"로그 레벨: {config.get_log_level()}")
        console.print(f"동기화 배치 크기: {config.get_sync_batch_size()}")
        console.print(f"동기화 간격(분): {config.get_sync_interval_minutes()}")
        
    except Exception as e:
        console.print(f"[red]오류: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
