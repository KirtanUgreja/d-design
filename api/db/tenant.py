"""The tenant transaction wrapper — the only place app.user_id is set in Python.

patterns.md rule 4: every tenant-scoped query runs inside this wrapper. Exactly
two wrappers, one per language; this is the Python one (the TypeScript one is
web/src/db/tenant.ts). The `true` in set_config scopes the value to the
transaction, which is what keeps a pooled connection from serving the previous
user.

A third file that sets app.user_id is a bug the invariants script fails on
(scripts/checks/invariants.sh, EXPECTED_TENANT_WRAPPERS=2).
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import session_factory


@contextlib.asynccontextmanager
async def as_user(user_id: str) -> AsyncIterator[AsyncSession]:
    """Run a block of queries as ``user_id``.

    The session variable is scoped to the transaction via the trailing ``true``
    — without it, a connection returned to the pool would serve the next
    request as the previous user.
    """
    async with session_factory() as session, session.begin():
        await session.execute(
            text("select set_config('app.user_id', :uid, true)"),
            {"uid": user_id},
        )
        yield session
