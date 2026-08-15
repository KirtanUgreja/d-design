"""Session-resolution tests — the fail-closed spine (v3, phase 16).

resolve_session must fail closed (patterns.md rule 5, OWASP A10): a missing
token, an expired session, an unreadable database, and a session that does
not exist all return Unauthorized. There is no permissive default — no
default user, no grant on error.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from auth.session_data import Unauthorized, resolve_session
from lib.result import Err, Ok, Result, err, ok

Lookup = Callable[[str], Awaitable[Result[tuple[str, datetime], Unauthorized]]]


def _future() -> datetime:
    return datetime.now(UTC) + timedelta(hours=1)


def _expired() -> datetime:
    return datetime.now(UTC) - timedelta(hours=1)


def _lookup(row: tuple[str, datetime] | None = None, error: Exception | None = None) -> Lookup:
    async def lookup(token: str) -> Result[tuple[str, datetime], Unauthorized]:
        del token
        if error is not None:
            raise error
        if row is None:
            return err(Unauthorized())
        return ok(row)

    return lookup


def _run[T](coro: Awaitable[T]) -> T:
    return asyncio.run(coro)


def test_empty_token_fails_closed() -> None:
    result = _run(resolve_session(""))
    assert isinstance(result, Err)
    assert isinstance(result.error, Unauthorized)


def test_missing_row_fails_closed() -> None:
    result = _run(resolve_session("token", _lookup(row=None)))
    assert isinstance(result, Err)
    assert isinstance(result.error, Unauthorized)


def test_expired_session_fails_closed() -> None:
    result = _run(resolve_session("token", _lookup(row=("user-1", _expired()))))
    assert isinstance(result, Err)
    assert isinstance(result.error, Unauthorized)


def test_unreadable_database_fails_closed_not_grants() -> None:
    # The dangerous shape: a catch returning a permissive default. The
    # resolver must refuse when the lookup raises, never grant.
    result = _run(resolve_session("token", _lookup(error=RuntimeError("db down"))))
    assert isinstance(result, Err)
    assert isinstance(result.error, Unauthorized)


def test_valid_session_resolves() -> None:
    result = _run(resolve_session("token", _lookup(row=("user-1", _future()))))
    assert isinstance(result, Ok)
    assert result.value == "user-1"
