"""Alembic migration environment.

Migrates the APP tables only. The auth tables are owned by web (Better Auth,
Drizzle); Alembic must never propose dropping them, so include_object excludes
them — this is the single most destructive failure mode in the architecture
(docs/techstack/backend.md), and the filter below is what prevents it.

The engine is api's async engine (db/session.py); migrations run in a sync
context via a temp sync engine over the same URL (Alembic's standard async
pattern). The migration role owns DDL; the app role (no bypassrls) never does.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Literal

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.sql.schema import SchemaItem

from db.session import database_url

# The seven auth tables owned by web (Better Auth, Drizzle). Alembic must never
# propose dropping them — this is the single most destructive failure mode in
# the architecture (docs/techstack/backend.md).
AUTH_TABLES = frozenset(
    {"user", "session", "account", "verification", "organization", "member", "invitation"}
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", database_url())


def include_object(
    object_: SchemaItem,
    name: str | None,
    type_: Literal[
        "schema",
        "table",
        "column",
        "index",
        "unique_constraint",
        "foreign_key_constraint",
        "check_constraint",
    ],
    reflected: bool,
    compare_to: SchemaItem | None,
) -> bool:
    """Exclude the auth tables from autogenerate. A table Alembic does not know
    it owns must not be something Alembic proposes to drop.

    ``object_`` and ``compare_to`` are Alembic's migration context objects; we
    only branch on ``type_`` and ``name``.
    """
    del reflected, compare_to
    if type_ == "table":
        return name not in AUTH_TABLES
    return True


# Set when alembic runs; the invariant in scripts/checks/invariants.sh greps for
# `include_object=include_object` to confirm the wiring survived.
include_object = include_object


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL emitted, not executed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        include_object=include_object,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=None,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations online against the async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (executed against the database)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
