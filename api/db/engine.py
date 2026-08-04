"""The engine and the session factory. Nothing here knows about tenants —
that is `tenant.py`, and it is deliberately the only door."""

from functools import cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import config


def _url() -> str:
    # asyncpg caches prepared statements per connection. Behind a
    # transaction-mode pooler the connection you get back is not the one that
    # built the cache, and the errors that produces look like nothing else in
    # the system. Disable it here rather than debugging it in staging.
    url = config().database_url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}prepared_statement_cache_size=0"


@cache
def engine() -> AsyncEngine:
    return create_async_engine(_url(), pool_pre_ping=True)


@cache
def session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine(), expire_on_commit=False)
