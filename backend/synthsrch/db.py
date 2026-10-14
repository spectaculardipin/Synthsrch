"""Async SQLite engine + session helper."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings
from .models import Base


def _db_url() -> str:
    return f"sqlite+aiosqlite:///{get_settings().db_path}"


_engine = None
_SessionFactory = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(_db_url(), future=True)
    return _engine


def session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = async_sessionmaker(engine(), class_=AsyncSession, expire_on_commit=False)
    return _SessionFactory


async def init_db() -> None:
    async with engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
