"""Tenant-wrapper tests — the unset case (v3, phase 16).

patterns.md rule 4 + tenancy-and-data.md: `current_setting('app.user_id')` on
a connection where it was never set must FAIL, not match everything. That is
the failure mode that turns pooling into a cross-tenant read.

These tests need a live Postgres (docker compose up -d postgres). They skip
when the DB is unreachable so the deterministic gate stays green without the
daemon running — but they are the phase's real fail-closed verification.
"""

from __future__ import annotations

from collections.abc import Awaitable

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from db.session import database_url, session_factory
from db.tenant import as_user
from tests.rls_helper import run_on_loop


def _run[T](coro: Awaitable[T]) -> T:
    return run_on_loop(coro)


async def _db_is_up() -> bool:
    try:
        async with session_factory() as session:
            await session.execute(text("select 1"))
        return True
    except Exception:
        return False


def test_unset_app_user_id_fails_closed() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")

    # A connection with no app.user_id set must raise on read — never return a
    # value that matches every tenant (pooling -> cross-tenant read). The
    # `true` in current_setting suppresses the error, so this explicitly uses
    # the failing form. NullPool guarantees a genuinely fresh connection.
    async def _probe() -> None:
        engine = create_async_engine(database_url(), poolclass=NullPool)
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(text("select current_setting('app.user_id')"))
                result.first()
        finally:
            await engine.dispose()

    with pytest.raises(ProgrammingError):
        _run(_probe())


def test_as_user_sets_the_variable_scoped_to_the_transaction() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")
    # A valid UUID so the value round-trips against the ::uuid RLS casts.
    user_id = "00000000-0000-0000-0000-0000000000aa"

    async def _probe() -> None:
        async with as_user(user_id) as session:
            row = (
                await session.execute(text("select current_setting('app.user_id', true)"))
            ).first()
            assert row is not None
            assert row[0] == user_id

    _run(_probe())
