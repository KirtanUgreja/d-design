"""Session resolution — the one place api touches an auth table, read-only.

backend.md -> "Session resolution": Better Auth issues sessions in web; api
resolves them by reading the `session` table directly. This is the documented
exception to table ownership — api reads auth tables, never writes them, and
this module is the only place it does.

It fails closed (patterns.md rule 5, OWASP A10): no row, expired row, or
unreadable database all return Unauthorized. There is no permissive default.
The better-auth session schema shape (token, user_id, expires_at) is pinned by
the better-auth version; a major upgrade touches both repos in one session.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import text

from db.session import session_factory
from lib.result import Err, Result, err, ok

# The read-only query over the auth session table. `expires_at` is stored as
# a timestamp; the exact column set is better-auth's schema (pinned version).
#
# Matched on `token`, not `id`: the bearer carries the session token — the
# value Better Auth puts in its cookie — while `id` is a separate primary key
# that never leaves the database. Matching on `id` made every real session
# resolve to Unauthorized.
SELECT_SESSION = text("select user_id, expires_at from auth.session where token = :token")


@dataclass(frozen=True)
class Unauthorized:
    detail: str = "session is missing, expired, or unreadable"


async def _lookup_session(token: str) -> Result[tuple[str, datetime], Unauthorized]:
    """The production session lookup: read the auth session table read-only.

    A missing row or an unreadable database both return Unauthorized — the
    fail-closed spine (no permissive default).
    """
    try:
        async with session_factory() as session:
            row = (await session.execute(SELECT_SESSION, {"token": token})).first()
    except Exception:
        # An unreadable database must refuse, not grant (rule 5).
        return err(Unauthorized())

    if row is None:
        return err(Unauthorized())
    return ok((row[0], row[1]))


async def resolve_session(
    token: str,
    lookup: Callable[[str], Awaitable[Result[tuple[str, datetime], Unauthorized]]] | None = None,
) -> Result[str, Unauthorized]:
    """Resolve a Better Auth session token to a user_id.

    Fails closed: missing token, expired session, and any database error all
    return Unauthorized — never a default user and never a grant. ``lookup``
    is the seam tests inject; production uses ``_lookup_session``.
    """
    if not token:
        return err(Unauthorized())

    fn = lookup if lookup is not None else _lookup_session
    try:
        result = await fn(token)
    except Exception:
        # An unreadable database must refuse, not grant (rule 5) — the
        # fail-closed spine holds regardless of which lookup failed.
        return err(Unauthorized())
    if isinstance(result, Err):
        return result

    user_id, expires_at = result.value
    # The auth table stores expires_at as a naive timestamp (no tz); normalize
    # so the comparison never mixes aware and naive datetimes (a 500 that
    # would fail closed but loudly — surfaced by the live end-to-end run).
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        return err(Unauthorized())

    return ok(user_id)
