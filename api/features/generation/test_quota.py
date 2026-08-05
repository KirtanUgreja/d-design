"""Quota and the kill switch, against the real database — the race in
particular does not show up in a sequential test
(docs/security/testing.md -> "Failing closed" -> "The race").
"""

import asyncio
import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from features.generation.quota import check_quota_and_kill_switch, log_generation
from lib.result import Err, Ok

_MIGRATOR = os.environ["MIGRATION_DATABASE_URL"]

_INSERT = text(
    'insert into quotas (owner_id, used, "limit", halted) '
    "values (:owner, :used, :limit_, :halted)"
)
_DELETE = text("delete from quotas where owner_id = :owner")
_DELETE_GENERATIONS = text("delete from generations where owner_id = :owner")


@pytest.fixture
async def quota_row() -> AsyncIterator[tuple[str, UUID]]:
    """A fresh `quotas` row per test, isolated from the shared
    `LOCAL_USER_ID` seed row — a race test against a shared row would be
    flaky against whatever another test already consumed."""
    owner_id = uuid4()
    engine = create_async_engine(_MIGRATOR)
    async with engine.begin() as conn:
        await conn.execute(
            _INSERT, {"owner": owner_id, "used": 0, "limit_": 1, "halted": False}
        )
    yield str(owner_id), owner_id
    async with engine.begin() as conn:
        await conn.execute(_DELETE_GENERATIONS, {"owner": owner_id})
        await conn.execute(_DELETE, {"owner": owner_id})
    await engine.dispose()


async def test_first_call_succeeds_second_is_refused(
    quota_row: tuple[str, UUID],
) -> None:
    owner_id, _ = quota_row
    first = await check_quota_and_kill_switch(owner_id)
    second = await check_quota_and_kill_switch(owner_id)
    assert isinstance(first, Ok)
    assert isinstance(second, Err)
    assert second.error.code == "quota_exceeded"


async def test_halted_row_refuses_even_with_balance_remaining() -> None:
    owner_id = uuid4()
    engine = create_async_engine(_MIGRATOR)
    async with engine.begin() as conn:
        await conn.execute(
            _INSERT, {"owner": owner_id, "used": 0, "limit_": 1000, "halted": True}
        )
    try:
        result = await check_quota_and_kill_switch(str(owner_id))
        assert isinstance(result, Err)
        assert result.error.code == "quota_exceeded"
    finally:
        async with engine.begin() as conn:
            await conn.execute(_DELETE, {"owner": owner_id})
        await engine.dispose()


async def test_unknown_owner_is_refused_not_a_crash() -> None:
    """No row at all — the same "no row came back" path a halted or
    exhausted quota takes, not a special case."""
    result = await check_quota_and_kill_switch(str(uuid4()))
    assert isinstance(result, Err)
    assert result.error.code == "quota_exceeded"


async def test_n_parallel_requests_against_a_balance_of_one_exactly_one_succeeds(
    quota_row: tuple[str, UUID],
) -> None:
    """The race docs/security/testing.md names explicitly: it does not show
    up in a sequential test, only under real concurrency against the same
    row."""
    owner_id, _ = quota_row
    results = await asyncio.gather(
        *(check_quota_and_kill_switch(owner_id) for _ in range(10))
    )
    oks = [r for r in results if isinstance(r, Ok)]
    errs = [r for r in results if isinstance(r, Err)]
    assert len(oks) == 1
    assert len(errs) == 9
    assert all(e.error.code == "quota_exceeded" for e in errs)


async def test_log_generation_writes_metadata_only(
    quota_row: tuple[str, UUID],
) -> None:
    owner_id, owner_uuid = quota_row
    experience_id = uuid4()
    await log_generation(
        owner_id=owner_id,
        experience_id=str(experience_id),
        phase="build",
        model_id="test/model",
        provider_route="openrouter",
        tokens_in=100,
        tokens_out=50,
        cached_tokens=10,
        calls=1,
        repaired=False,
        error_class=None,
        duration_ms=1234,
    )

    engine = create_async_engine(_MIGRATOR)
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "select phase, model_id, tokens_in, tokens_out, calls, repaired "
                    "from generations where owner_id = :owner"
                ),
                {"owner": owner_uuid},
            )
        ).one()
    await engine.dispose()

    assert row.phase == "build"
    assert row.model_id == "test/model"
    assert row.tokens_in == 100
    assert row.tokens_out == 50
    assert row.calls == 1
    assert row.repaired is False
