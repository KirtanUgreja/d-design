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
        # The role switch is what makes the policies apply at all. A role with
        # `rolbypassrls` — a superuser, or a table's owner — skips row-level
        # security entirely, so `app.user_id` would be set and then ignored.
        # The local compose database connects as `ddesign`, which is a
        # superuser, so without this line RLS is inert wherever the stack is
        # run for real: GET /experiences returned every tenant's rows.
        #
        # `app_user` is the nologin role migration 0001 creates with no
        # bypassrls, and it holds the table grants (0005, 0008). Production
        # connects as that role directly, where setting a role to itself is a
        # no-op — so this is the same transaction in both.
        #
        # LOCAL, not SET: scoped to the transaction, so a pooled connection
        # cannot hand the next request a switched role (same reason as the
        # `true` above).
        #
        # The session resolver runs before this wrapper and stays on the owner
        # role — it reads web's `auth.session`, which app_user has no grant on.
        await session.execute(text("set local role app_user"))
        yield session
