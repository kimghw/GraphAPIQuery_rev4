"""
데이터베이스 관리 CLI 명령어

데이터베이스 초기화, 마이그레이션 등을 위한 CLI 명령어입니다.
"""

import asyncio
import typer
from rich.console import Console

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
            
            # 데이터베이스 리셋 (테이블 삭제 후 재생성)
            await db_adapter.reset()
            
            console.print("[green]✓ 데이터베이스 리셋이 완료되었습니다![/green]")
            
            await db_adapter.close()
            
        except Exception as e:
            console.print(f"[red]오류: {str(e)}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_reset())


if __name__ == "__main__":
    app()
