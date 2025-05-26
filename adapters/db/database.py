"""
데이터베이스 연결 및 세션 관리

SQLAlchemy 비동기 엔진과 세션 관리를 담당합니다.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.domain.ports import ConfigPort
from .models import Base


class DatabaseAdapter:
    """데이터베이스 어댑터"""
    
    def __init__(self, config: ConfigPort):
        self.config = config
        self.engine: AsyncEngine = None
        self.session_factory: sessionmaker = None
    
    async def initialize(self) -> None:
        """데이터베이스 연결을 초기화합니다."""
        database_url = self.config.get_database_url()
        
        # 비동기 엔진 생성
        self.engine = create_async_engine(
            database_url,
            echo=False,  # SQL 로깅 (개발 시에만 True)
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # 연결 상태 확인
            pool_recycle=3600,   # 1시간마다 연결 재생성
        )
        
        # 세션 팩토리 생성
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def create_tables(self) -> None:
        """데이터베이스 테이블을 생성합니다."""
        if self.engine is None:
            raise RuntimeError("데이터베이스가 초기화되지 않았습니다")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self) -> None:
        """데이터베이스 테이블을 삭제합니다."""
        if self.engine is None:
            raise RuntimeError("데이터베이스가 초기화되지 않았습니다")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """데이터베이스 세션을 생성합니다."""
        if self.session_factory is None:
            raise RuntimeError("데이터베이스가 초기화되지 않았습니다")
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self) -> None:
        """데이터베이스 연결을 종료합니다."""
        if self.engine:
            await self.engine.dispose()


# 전역 데이터베이스 어댑터 인스턴스
_database_adapter: DatabaseAdapter = None


def get_database_adapter() -> DatabaseAdapter:
    """전역 데이터베이스 어댑터를 반환합니다."""
    global _database_adapter
    if _database_adapter is None:
        raise RuntimeError("데이터베이스 어댑터가 초기화되지 않았습니다")
    return _database_adapter


def initialize_database(config: ConfigPort) -> DatabaseAdapter:
    """데이터베이스 어댑터를 초기화합니다."""
    global _database_adapter
    _database_adapter = DatabaseAdapter(config)
    return _database_adapter


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """데이터베이스 세션을 생성하는 의존성 주입 함수"""
    db_adapter = get_database_adapter()
    async with db_adapter.get_session() as session:
        yield session
