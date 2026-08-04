"""The tenant wrapper. The most dangerous code in the backend.

This is the only place `app.user_id` is set in Python, and a lint rule counts
the files that contain that string so "only" is a fact rather than a claim
(scripts/checks/invariants.sh). There is exactly one wrapper today; a second
arrives in `web` with Better Auth in v3, and raising the count is a deliberate
edit to the rule rather than a silent widening.

Three things are load-bearing and all three are invisible in review:

  * The `true` scopes the setting to the transaction. Without it the value
    persists on the connection, and a pooled connection handed to the next
    request serves it as the previous user. One boolean between correct and a
    cross-tenant read.
  * The pooler must run in transaction mode. Session mode binds a connection
    for a whole client session, which is the wrong lifetime for a web tier and
    silently breaks the scoping above.
  * A tenant-scoped query outside a transaction is unsafe by construction on a
    shared pool.

docs/coderules/patterns.md -> rule 4
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.engine import session_factory

_SET_TENANT = text("select set_config('app.user_id', :uid, true)")


@asynccontextmanager
async def as_user(user_id: str) -> AsyncIterator[AsyncSession]:
    sessions = session_factory()
    async with sessions() as s, s.begin():
        await s.execute(_SET_TENANT, {"uid": user_id})
        yield s
