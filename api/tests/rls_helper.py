"""RLS test helper — runs tenant-scoped queries as the app_user role.

The local compose DB connects as `ddesign`, which is a superuser — and
superusers BYPASS row-level security (the RLS tests would be meaningless:
an "outsider" could read anything). This helper switches the session to the
`app_user` role (no bypassrls, created by migration 0001) so the RLS policies
actually apply. In production the app connects as a non-bypassrls role
directly; this is the local-stack spelling of the same fact.

The role switch is transactional (SET LOCAL), so it cannot leak into a pooled
connection's next user — the same discipline as app.user_id itself.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Awaitable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.tenant import as_user

# ONE event loop for the whole test suite: session_factory() is a module-
# global engine whose pool binds connections to the loop that created them.
# Every test file that touches the DB must run on this same loop, or a pooled
# connection is handed to a different loop ("Future attached to a different
# loop"). Each file imports `_run` from here rather than making its own loop.
LOOP = asyncio.new_event_loop()


def run_on_loop[T](coro: Awaitable[T]) -> T:
    return LOOP.run_until_complete(coro)


@contextlib.asynccontextmanager
async def as_app_user(user_id: str) -> AsyncIterator[AsyncSession]:
    """Like as_user, but the session runs as app_user so RLS applies."""
    async with as_user(user_id) as session:
        await session.execute(text("set local role app_user"))
        yield session
