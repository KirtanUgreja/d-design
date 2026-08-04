"""Alembic environment.

The `include_object` filter below is the most important thing in this file.
Two migration tools run against one database, and the only thing preventing
them from destroying each other's schema is that their table sets are disjoint.
Without this filter, an autogenerate run sees seven tables it does not know
about and helpfully writes a migration to delete them — the single most
destructive failure mode in this architecture, one config block away.

docs/techstack/backend.md -> "Two ORMs, one database"
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Better Auth's tables, owned by Drizzle in `web`. `api` may read `user` and
# `session`; it never writes them and never migrates them.
AUTH_TABLES = frozenset(
    {
        "user",
        "session",
        "account",
        "verification",
        "organization",
        "member",
        "invitation",
    }
)


def include_object(
    obj: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object,
) -> bool:
    if type_ == "table" and name in AUTH_TABLES:
        return False
    return True


def _url() -> str:
    url = os.environ.get("MIGRATION_DATABASE_URL")
    if not url:
        raise RuntimeError("MIGRATION_DATABASE_URL is not set (connect as `migrator`)")
    return url


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    section: dict[str, str] = dict(config.get_section(config.config_ini_section) or {})
    section["sqlalchemy.url"] = _url()
    engine = async_engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with engine.connect() as connection:
        await connection.run_sync(_do_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
