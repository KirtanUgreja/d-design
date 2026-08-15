"""brand_kits RLS tests — the tenant-isolation proof (phase 17).

The team-scoped policies do the isolation; this module never filters by user.
These tests need a live Postgres (docker compose up -d postgres) and skip
otherwise, like the phase-16 tenant tests.

They prove the three claims that must never silently regress:
  - a team member reads the kit (RLS grants);
  - a non-member gets NO row (RLS denies — not an empty list, a denial);
  - the unset app.user_id case fails (pooling -> cross-tenant read guard).

The reads run as app_user (rls_helper) — the compose superuser would bypass
RLS, which would make the denial assertion meaningless.
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


# User ids must be valid UUIDs: owner_id / user_id columns are sa.Uuid(), and
# RLS compares current_setting('app.user_id')::uuid. Fixed values keep the
# assertions readable.
OWNER = "00000000-0000-0000-0000-000000000001"
MEMBER = "00000000-0000-0000-0000-000000000002"
OUTSIDER = "00000000-0000-0000-0000-000000000003"


async def _create_team_with_kit(owner: str, member: str) -> tuple[str, str]:
    """Create a team owned by ``owner`` with ``member`` in it, plus a kit.
    Returns (team_id, kit_id). Runs as owner through the RLS helper so the
    with-check policies apply (the owner bootstraps the first membership)."""
    async with as_app_user(owner) as s:
        team_id = __import__("uuid").uuid4()
        kit_id = __import__("uuid").uuid4()
        await s.execute(
            text("insert into teams (id, owner_id, name) values (:id, :owner, 'Test Team')"),
            {"id": team_id, "owner": owner},
        )
        await s.execute(
            text(
                "insert into team_members (team_id, user_id, role)"
                " values (:team, :member, 'member')"
            ),
            {"team": team_id, "member": member},
        )
        await s.execute(
            text(
                "insert into brand_kits (id, team_id, name, colors_json, font_ids)"
                " values (:id, :team, 'Kit', '{\"accent\": \"#111111\"}', '[]')"
            ),
            {"id": kit_id, "team": team_id},
        )
    return str(team_id), str(kit_id)


def test_member_reads_kit_cross_team_denied() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")
    _team_id, kit_id = _run(_create_team_with_kit(OWNER, MEMBER))

    async def _member_read() -> object:
        async with as_app_user(MEMBER) as s:
            row = (
                await s.execute(text("select id from brand_kits where id = :k"), {"k": kit_id})
            ).first()
            return str(row[0]) if row else None

    async def _outsider_read() -> object:
        async with as_app_user(OUTSIDER) as s:
            row = (
                await s.execute(text("select id from brand_kits where id = :k"), {"k": kit_id})
            ).first()
            return str(row[0]) if row else None

    assert _run(_member_read()) == kit_id
    assert _run(_outsider_read()) is None


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
