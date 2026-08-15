"""The async engine and session factory — api's database layer (v3, phase 16).

One module-level engine, reused (python.md: "One httpx.AsyncClient, module-
level, reused" is the same rule for the DB). The engine connects as the app
role (no bypassrls) and every tenant-scoped query runs inside the as_user
wrapper (db/tenant.py).

The transaction-mode pooler note (backend.md): asyncpg caches prepared
statements, which breaks behind a transaction-mode pooler. Local Postgres via
Docker Compose is direct, so the cache stays; the moment RDS Proxy / PgBouncer
arrives, disable asyncpg's prepared-statement cache.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# The app connects as a role with no bypassrls; the migration role owns DDL.
DEFAULT_DATABASE_URL = "postgresql+asyncpg://ddesign:ddesign@localhost:5432/ddesign"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


_engine: AsyncEngine | None = None
_maker: async_sessionmaker[AsyncSession] | None = None


def engine() -> AsyncEngine:
    """The one module-level engine, created on first use."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(database_url(), pool_pre_ping=True)
    return _engine


def _session_maker() -> async_sessionmaker[AsyncSession]:
    """The one module-level session maker, created on first use."""
    global _maker
    if _maker is None:
        _maker = async_sessionmaker(engine(), expire_on_commit=False)
    return _maker


def session_factory() -> AsyncSession:
    """A session from the one module-level maker.

    Callers use `as_user` (db/tenant.py) rather than this directly for any
    tenant-scoped work; this is the raw session entry the wrapper builds on.
    """
    return _session_maker()()


async def dispose() -> None:
    """Close the engine — used by tests and shutdown."""
    global _engine, _maker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _maker = None
