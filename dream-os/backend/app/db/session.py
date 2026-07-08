"""Database Session - 数据库会话管理"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from ..models.base import Base

DATABASE_URL = "sqlite+aiosqlite:///./dream_os.db"
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={
        "timeout": 30,
        "check_same_thread": False,
    },
    poolclass=NullPool,

    pool_pre_ping=True,
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    # 导入所有模型，确保它们注册到 Base.metadata
    from ..models import setting, task, dev_task, log, media, memory, project  # noqa: F401
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=5000"))
        await conn.run_sync(Base.metadata.create_all)
