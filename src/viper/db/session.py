"""Async database session and engine setup."""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from viper.config import DATABASE_URL


def ensure_sqlite_dir(url: str) -> None:
    if url.startswith('sqlite+aiosqlite:///'):
        db_path = url.removeprefix('sqlite+aiosqlite:///')
        if db_path not in {':memory:', ''}:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)


ensure_sqlite_dir(DATABASE_URL)

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)

async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with async_session_maker() as session:
        yield session


async def init_db(engine_override: AsyncEngine | None = None) -> None:
    """Create all registered SQLModel tables in database."""
    target_engine = engine_override or engine
    async with target_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
