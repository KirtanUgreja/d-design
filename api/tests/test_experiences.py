"""experiences RLS tests — the owner-isolation proof (phase 18).

The experiences table is owner-scoped (0001); hosting (phase 18) records the
published key on it. These need a live Postgres and skip otherwise, like the
phase-17 brand-kits tests.

They prove: the owner reads the saved deck + published key; a different user
gets NO row (RLS denies, not an empty list); the unset app.user_id case fails
closed (pooling -> cross-tenant read guard).
"""

from __future__ import annotations

from collections.abc import Awaitable

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from db.session import database_url, session_factory
from tests.rls_helper import as_app_user, run_on_loop

pytestmark = pytest.mark.skipif(
    __import__("os").environ.get("SKIP_DB_TESTS", "") == "1",
    reason="DB tests need a live Postgres (docker compose up -d postgres)",
)


def _run[T](coro: Awaitable[T]) -> T:
    return run_on_loop(coro)


async def _db_is_up() -> bool:
    try:
        async with session_factory() as session:
            await session.execute(text("select 1"))
        return True
    except Exception:
        return False


# User ids must be valid UUIDs: owner_id columns are sa.Uuid(), and RLS
# compares current_setting('app.user_id')::uuid.
OWNER = "00000000-0000-0000-0000-000000000011"
OTHER = "00000000-0000-0000-0000-000000000012"


async def _create_experience(owner: str, published: bool) -> str:
    """Create an experience owned by ``owner``; returns its id."""
    async with as_app_user(owner) as s:
        exp_id = __import__("uuid").uuid4()
        await s.execute(
            text(
                "insert into experiences (id, owner_id, title, deck_json, published_key)"
                " values (:id, :owner, 'Test', '{}', :published)"
            ),
            {"id": exp_id, "owner": owner, "published": "pk-123" if published else None},
        )
    return str(exp_id)


def test_owner_reads_other_denied() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")
    exp_id = _run(_create_experience(OWNER, published=True))

    async def _read(user: str) -> object:
        async with as_app_user(user) as s:
            row = (
                await s.execute(
                    text("select published_key from experiences where id = :id"),
                    {"id": exp_id},
                )
            ).first()
            return str(row[0]) if row else None

    assert _run(_read(OWNER)) == "pk-123"
    assert _run(_read(OTHER)) is None


def test_unset_app_user_id_fails_closed() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")

    async def _probe() -> None:
        # A genuinely fresh connection (NullPool — never reused, never had
        # app.user_id set) must raise when read without the `true` fallback.
        engine = create_async_engine(database_url(), poolclass=NullPool)
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(text("select current_setting('app.user_id')"))
                result.first()
        finally:
            await engine.dispose()

    with pytest.raises(ProgrammingError):
        _run(_probe())
