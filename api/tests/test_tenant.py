"""Tenant-wrapper tests — the unset case (v3, phase 16).

patterns.md rule 4 + tenancy-and-data.md: `current_setting('app.user_id')` on
a connection where it was never set must FAIL, not match everything. That is
the failure mode that turns pooling into a cross-tenant read.

These tests need a live Postgres (docker compose up -d postgres). They skip
when the DB is unreachable so the deterministic gate stays green without the
daemon running — but they are the phase's real fail-closed verification.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from db.session import dispose, session_factory
from db.tenant import as_user


def _run[T](coro: Awaitable[T]) -> T:
    return asyncio.run(coro)


async def _db_is_up() -> bool:
    try:
        async with session_factory() as session:
            await session.execute(text("select 1"))
        return True
    except Exception:
        return False


def _teardown() -> None:
    _run(dispose())


def test_unset_app_user_id_fails_closed() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")
    try:
        # A connection with no app.user_id set must raise on read — never
        # return a value that matches every tenant (pooling -> cross-tenant
        # read). The `true` in current_setting suppresses the error, so this
        # explicitly uses the failing form.
        async def _probe() -> None:
            async with session_factory() as session:
                result = await session.execute(text("select current_setting('app.user_id')"))
                result.first()

        with pytest.raises(ProgrammingError):
            _run(_probe())
    finally:
        _teardown()


def test_as_user_sets_the_variable_scoped_to_the_transaction() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")
    try:

        async def _probe() -> None:
            async with as_user("user-1") as session:
                row = (
                    await session.execute(text("select current_setting('app.user_id', true)"))
                ).first()
                assert row is not None
                assert row[0] == "user-1"

        _run(_probe())
    finally:
        _teardown()
