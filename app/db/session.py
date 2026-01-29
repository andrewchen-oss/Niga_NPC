"""
[INPUT]: 依赖 app.config 的 get_settings, app.db.base 的 Base
[OUTPUT]: 对外提供 init_db, get_async_session
[POS]: db 模块的会话管理层，被 stream/processor 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.base import Base

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_async_session():
    """获取异步数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
