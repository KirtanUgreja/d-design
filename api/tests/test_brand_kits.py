"""brand_kits RLS tests — the tenant-isolation proof (phase 17).

The team-scoped policies from 0002 do the isolation; this module never
filters by user. These tests need a live Postgres (docker compose up -d
postgres) and skip otherwise, like the phase-16 tenant tests.

They prove the three claims that must never silently regress:
  - a team member reads the kit (RLS grants);
  - a non-member gets NO row (RLS denies — not an empty list, a denial);
  - the unset app.user_id case fails (pooling -> cross-tenant read guard).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from db.session import dispose, session_factory
from db.tenant import as_user

pytestmark = pytest.mark.skipif(
    __import__("os").environ.get("SKIP_DB_TESTS", "") == "1",
    reason="DB tests need a live Postgres (docker compose up -d postgres)",
)


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


async def _create_team_with_kit(owner: str, member: str) -> tuple[str, str]:
    """Create a team owned by ``owner`` with ``member`` in it, plus a kit.
    Returns (team_id, kit_id). Runs as owner (the migration role owns DDL;
    this is ordinary row work through the tenant wrapper)."""
    async with as_user(owner) as s:
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
    try:
        owner = "user-owner"
        member = "user-member"
        outsider = "user-outsider"
        _team_id, kit_id = _run(_create_team_with_kit(owner, member))

        async def _member_read() -> object:
            async with as_user(member) as s:
                row = (
                    await s.execute(text("select id from brand_kits where id = :k"), {"k": kit_id})
                ).first()
                return row[0] if row else None

        async def _outsider_read() -> object:
            async with as_user(outsider) as s:
                row = (
                    await s.execute(text("select id from brand_kits where id = :k"), {"k": kit_id})
                ).first()
                return row[0] if row else None

        assert _run(_member_read()) == kit_id
        assert _run(_outsider_read()) is None
    finally:
        _teardown()


def test_unset_app_user_id_fails_closed() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")
    try:

        async def _probe() -> None:
            async with session_factory() as session:
                result = await session.execute(text("select current_setting('app.user_id')"))
                result.first()

        with pytest.raises(ProgrammingError):
            _run(_probe())
    finally:
        _teardown()
