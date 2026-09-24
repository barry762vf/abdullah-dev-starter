"""Async PostgreSQL engine and request-scoped session dependency."""

from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def connect_args(settings: Settings) -> dict[str, object]:
    args: dict[str, object] = {"timeout": 5}
    if settings.database_transaction_pooler:
        # PgBouncer/Supavisor transaction mode may run each statement on a different server
        # connection, so asyncpg must not cache or reuse named prepared statements.
        args |= {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        }
    return args


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=1800,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args=connect_args(settings),
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one session; its caller controls commit/rollback per transaction."""
    async with request.app.state.session_factory() as session:
        yield session
