"""Isolation, proven rather than assumed.

This is the most important test file in phase 00. Rule 9 replaced a structural
guarantee with a procedural one, and a procedural guarantee that is not tested
is a comment.
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from db.engine import session_factory
from db.tenant import as_user

USER_A = "00000000-0000-4000-8000-00000000000a"
USER_B = "00000000-0000-4000-8000-00000000000b"

INSERT = text(
    "insert into experiences (owner_id, title, mode, art_direction, scenes) "
    "values (:owner, :title, 'scroll', 'cinematic-dark', '[]'::jsonb)"
)


@pytest.fixture
async def two_owners() -> AsyncIterator[None]:
    # Seeded as `migrator`, which owns the tables and is therefore not subject
    # to the policy — which is exactly what makes it the right role to seed
    # with, and the wrong one to serve requests with.
    engine = create_async_engine(os.environ["MIGRATION_DATABASE_URL"])
    async with engine.begin() as conn:
        await conn.execute(text("delete from experiences"))
        await conn.execute(INSERT, {"owner": USER_A, "title": "belongs to a"})
        await conn.execute(INSERT, {"owner": USER_B, "title": "belongs to b"})
    yield
    async with engine.begin() as conn:
        await conn.execute(text("delete from experiences"))
    await engine.dispose()


async def test_as_user_sees_exactly_its_own_rows(two_owners: None) -> None:
    async with as_user(USER_A) as session:
        rows = (
            (await session.execute(text("select title from experiences")))
            .scalars()
            .all()
        )
    assert list(rows) == ["belongs to a"]

    async with as_user(USER_B) as session:
        rows = (
            (await session.execute(text("select title from experiences")))
            .scalars()
            .all()
        )
    assert list(rows) == ["belongs to b"]


async def test_unset_tenant_fails_rather_than_matching_everything(
    two_owners: None,
) -> None:
    """The `true` in set_config, tested directly.

    Running `as_user` first is the point: it puts the setting on a pooled
    connection. If the third argument to set_config were missing, the value
    would persist on that connection and this next query — which never
    identified itself — would quietly return the previous user's rows. That is
    the cross-tenant read, and it is one boolean away.
    """
    async with as_user(USER_A) as session:
        await session.execute(text("select 1"))

    sessions = session_factory()
    with pytest.raises(DBAPIError) as caught:
        async with sessions() as session, session.begin():
            await session.execute(text("select title from experiences"))

    # Observed on Postgres 18: once set_config has run in a session the custom
    # parameter is registered, so the transaction-local value reverts to ""
    # rather than the parameter disappearing — and `''::uuid` raises
    # InvalidTextRepresentationError. Either wording is a refusal; what matters
    # is that the policy errors instead of evaluating to "matches everything".
    message = str(caught.value)
    assert "app.user_id" in message or "uuid" in message


async def test_with_check_blocks_writing_a_row_owned_by_someone_else() -> None:
    """`using` filters reads and `with check` filters writes. A policy with
    only the first lets a tenant insert a row it will never be able to see —
    which is a write primitive into another tenant's data."""
    with pytest.raises(DBAPIError):
        async with as_user(USER_A) as session:
            await session.execute(INSERT, {"owner": USER_B, "title": "smuggled"})
