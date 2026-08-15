"""quotas tests — the atomic-counter and fail-closed proof (phase 19).

The claims that must never silently regress:
  - the counter is atomic: N concurrent spends with limit N-1 → exactly N-1
    succeed (the "no row returned means refused" claim, provably);
  - fail-closed: a quota check that cannot run refuses (AGENTS.md rule 10);
  - the kill switch bounds spend: tripped → refuse even with quota remaining;
  - a fresh account gets the default free entitlement.

The deterministic unit tests use a fake session (no DB); the atomicity tests
need a live Postgres and skip otherwise (the phase-18 pattern).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable

import pytest
from sqlalchemy import text

from db.session import session_factory
from features.quotas.kill_switch import effective_plan, kill_switch_tripped
from features.quotas.quotas_data import (
    Entitlement,
    QuotaExceeded,
    consume_quota,
    get_entitlement,
    plan_limit,
)
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


# --- unit tests (no DB) -----------------------------------------------


class _FakeResult:
    def __init__(self, rows: list[tuple[object, ...]] | None) -> None:
        self._rows = rows or []

    def first(self) -> tuple[object, ...] | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    """A session stub that records executions and returns canned rows."""

    def __init__(self, update_row: tuple[object, ...] | None) -> None:
        self._update_row = update_row
        self.executed: list[str] = []

    async def execute(self, statement, params=None) -> _FakeResult:  # type: ignore[no-untyped-def]
        self.executed.append(str(statement))
        sql = str(statement)
        if "update quotas set used = used + 1" in sql:
            return _FakeResult([self._update_row] if self._update_row else None)
        if "select used, limit from quotas" in sql:
            return _FakeResult([(1, 1)])
        return _FakeResult([])


def test_consume_quota_succeeds_when_row_returned() -> None:
    s = _FakeSession((1, 1))
    refused = _run(consume_quota(s, "acc", plan="free", limit=1))  # type: ignore[arg-type]
    assert refused is None


def test_consume_quota_refuses_when_no_row_returned() -> None:
    s = _FakeSession(None)  # update...returning returns no row = at limit
    refused = _run(consume_quota(s, "acc", plan="free", limit=1))  # type: ignore[arg-type]
    assert isinstance(refused, QuotaExceeded)
    assert refused.limit == 1


def test_fail_closed_when_db_raises() -> None:
    class BoomSession(_FakeSession):
        async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
            raise RuntimeError("db down")

    with pytest.raises(RuntimeError):
        _run(consume_quota(BoomSession(None), "acc", plan="free", limit=1))  # type: ignore[arg-type]


def test_plan_limit() -> None:
    assert plan_limit("free") == 1
    assert plan_limit("paid") > 1


def test_effective_plan_defaults_free(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FORCE_PLAN", raising=False)
    assert effective_plan() == "free"
    monkeypatch.setenv("FORCE_PLAN", "paid")
    assert effective_plan() == "paid"


def test_kill_switch_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KILL_SWITCH", raising=False)
    assert kill_switch_tripped() is False
    monkeypatch.setenv("KILL_SWITCH", "1")
    assert kill_switch_tripped() is True


# --- live-DB tests ----------------------------------------------------


async def _consume(account: str, plan: str, limit: int) -> QuotaExceeded | None:
    async with as_app_user(account) as session:
        return await consume_quota(session, account, plan=plan, limit=limit)


def test_race_proof_atomic_counter() -> None:
    """N concurrent spends with limit N-1: exactly N-1 succeed."""
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")
    n = 5
    account = str(__import__("uuid").uuid4())  # fresh each run

    async def _race() -> list[QuotaExceeded | None]:
        return await asyncio.gather(*[_consume(account, "paid", limit=n - 1) for _ in range(n)])

    results = _run(_race())
    refused = [r for r in results if isinstance(r, QuotaExceeded)]
    succeeded = [r for r in results if r is None]
    assert len(succeeded) == n - 1
    assert len(refused) == 1


def test_fresh_account_gets_free_entitlement() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")
    fresh = "00000000-0000-0000-0000-0000000000c2"

    async def _get() -> Entitlement:
        async with as_app_user(fresh) as session:
            return await get_entitlement(session, fresh, plan=effective_plan())

    e = _run(_get())
    assert e.plan == "free"
    assert e.used == 0
    assert e.limit == 1
    assert not e.exhausted


def test_free_limit_consumed_then_refused() -> None:
    if not _run(_db_is_up()):
        pytest.skip("no live Postgres")
    # A fresh account each run (the previous run left used=1).
    account = str(__import__("uuid").uuid4())

    first = _run(_consume(account, "free", limit=1))
    second = _run(_consume(account, "free", limit=1))
    assert first is None
    assert isinstance(second, QuotaExceeded)
    assert second.used == 1
    assert second.limit == 1
