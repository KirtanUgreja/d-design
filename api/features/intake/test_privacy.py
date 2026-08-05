"""The exit-gate proof docs/v1/plan/08-intake.md asks for: "A canary string
typed into the interview appears in the `briefs` table and **nowhere else** —
not in logs, not in error output, not in `generations`."

A brief is the customer's unreleased launch messaging. The distinction between
a row in a table they own and a line in an error tracker is the whole of
docs/security/tenancy-and-data.md, and it is the kind of property that is true
until someone adds one convenient log line — so it is asserted, not assumed.

Also the `briefs` isolation test: the table's RLS policy proven with two
owners, the same shape as tests/test_tenancy.py.
"""

import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from db.tenant import as_user
from features.intake import load_brief, save_brief
from schema.brief import Brief, BriefCta

_MIGRATOR = os.environ["MIGRATION_DATABASE_URL"]

USER_A = UUID("00000000-0000-4000-8000-00000000000a")
USER_B = UUID("00000000-0000-4000-8000-00000000000b")


def _brief(canary: str) -> Brief:
    return Brief(
        goal=f"Launch {canary}",
        audience="Backend engineers",
        key_messages=[f"{canary} ships today", "It is fast", "It is cheap"],
        proof_points=[f"{canary} cut latency 40%"],
        tone="confident",
        cta=BriefCta(label="Start", href="https://example.com/start"),
        constraints=f"never say {canary} is beta",
    )


@pytest.fixture
async def clean_briefs() -> AsyncIterator[None]:
    engine = create_async_engine(_MIGRATOR)
    async with engine.begin() as conn:
        await conn.execute(text("delete from briefs"))
    yield
    async with engine.begin() as conn:
        await conn.execute(text("delete from briefs"))
    await engine.dispose()


async def test_canary_lands_in_briefs_and_nowhere_else(clean_briefs: None) -> None:
    canary = f"CANARY-{uuid4()}"
    experience_id = uuid4()

    async with as_user(str(USER_A)) as session:
        await save_brief(
            session, owner_id=USER_A, experience_id=experience_id, brief=_brief(canary)
        )

    engine = create_async_engine(_MIGRATOR)
    try:
        async with engine.begin() as conn:
            stored = (
                await conn.execute(text("select payload::text from briefs"))
            ).scalar_one()
            assert canary in stored, "the brief must be stored — it is the record"

            # Every other table that could plausibly have picked it up,
            # written out rather than built from a loop variable — a test
            # that constructs SQL from strings teaches the pattern that
            # a non-test file then copies. `generations` matters most: a
            # brief passes through the seam on its way to the Director.
            elsewhere = (
                "select coalesce(string_agg(phase || model_id, ' '), '') from generations",
                "select coalesce(string_agg(title, ' '), '') from experiences",
            )
            for query in elsewhere:
                assert canary not in (await conn.execute(text(query))).scalar_one()
    finally:
        await engine.dispose()


async def test_a_stored_brief_reads_back_as_the_same_brief(
    clean_briefs: None,
) -> None:
    """Round trip through `jsonb`. `save_brief` writes `by_alias=True`, so
    this also proves the stored shape is the camelCase contract every other
    reader of a Brief sees, not a Python-private encoding."""
    canary = f"CANARY-{uuid4()}"
    experience_id = uuid4()
    original = _brief(canary)

    async with as_user(str(USER_A)) as session:
        await save_brief(
            session, owner_id=USER_A, experience_id=experience_id, brief=original
        )
    async with as_user(str(USER_A)) as session:
        loaded = await load_brief(session, experience_id=experience_id)

    assert loaded == original


async def test_briefs_are_isolated_by_owner(clean_briefs: None) -> None:
    """The isolation test the exit gate asks for. B's brief is invisible to A
    through the same `as_user` door every tenant-scoped query uses."""
    a_experience, b_experience = uuid4(), uuid4()

    async with as_user(str(USER_A)) as session:
        await save_brief(
            session,
            owner_id=USER_A,
            experience_id=a_experience,
            brief=_brief("BELONGS-TO-A"),
        )
    async with as_user(str(USER_B)) as session:
        await save_brief(
            session,
            owner_id=USER_B,
            experience_id=b_experience,
            brief=_brief("BELONGS-TO-B"),
        )

    async with as_user(str(USER_A)) as session:
        assert await load_brief(session, experience_id=a_experience) is not None
        # The row exists; the policy is what makes it unreachable.
        assert await load_brief(session, experience_id=b_experience) is None


async def test_a_brief_cannot_be_written_on_another_owners_behalf(
    clean_briefs: None,
) -> None:
    """`with check`, not just `using`. Without it a tenant can read only their
    own rows while happily inserting rows owned by someone else."""
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError):
        async with as_user(str(USER_A)) as session:
            await save_brief(
                session,
                owner_id=USER_B,
                experience_id=uuid4(),
                brief=_brief("SMUGGLED"),
            )
