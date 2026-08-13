"""The tenant transaction wrapper — the only place app.user_id is set in Python.

patterns.md rule 4: every tenant-scoped query runs inside this wrapper. Exactly
one wrapper per language; this is the Python one. The `true` in set_config
scopes the value to the transaction, which is what keeps a pooled connection
from serving the previous user.

v1 has no database (the DB and multi-tenancy arrive in v3). This module exists
so the tenant-isolation invariant in scripts/checks/invariants.sh has its one
named home from day one, and the shape is right before anything queries it.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection

# Note: sqlalchemy is a baseline dependency for api (docs/coderules/dependencies.md)
# but is not installed in v1 since v1 has no database. The import stays lazy
# (TYPE_CHECKING above, __import__ below) until the DB lands in v3, so the gate
# can typecheck this file without requiring the package yet.


@contextlib.asynccontextmanager
async def as_user(user_id: str, connection: AsyncConnection) -> AsyncIterator[AsyncConnection]:
    """Run a block of queries as ``user_id``.

    The session variable is scoped to the transaction via the trailing ``true``.
    """
    await connection.execute(
        __import__("sqlalchemy").text("select set_config('app.user_id', :uid, true)"),
        {"uid": user_id},
    )
    yield connection
