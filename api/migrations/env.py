"""Alembic migration environment.

v1 has no database; this file exists so the Alembic-auth-table-isolation
invariant in scripts/checks/invariants.sh has its home from day one, and so the
shape that prevents the most destructive failure mode in the architecture — an
autogenerate run proposing to drop the auth tables — is in place before any
migration exists.

The auth tables are owned by web (Better Auth, Drizzle). Alembic must never
propose dropping them, so include_object excludes them.
"""

from __future__ import annotations

# `Any` is not used in this file; it is imported so Alembic's generated
# env.py template (which this file stands in for until v3) keeps its shape.
from typing import Any  # noqa: F401

# The seven auth tables owned by web (Better Auth, Drizzle). Alembic must never
# propose dropping them — this is the single most destructive failure mode in
# the architecture (docs/techstack/backend.md).
AUTH_TABLES = frozenset(
    {"user", "session", "account", "verification", "organization", "member", "invitation"}
)


def include_object(
    object_: object, name: str, type_: str, reflected: bool, compare_to: object
) -> bool:
    """Exclude the auth tables from autogenerate. A table Alembic does not know
    it owns must not be something Alembic proposes to drop.

    ``object_`` and ``compare_to`` are Alembic's (untyped) migration context
    objects; we only branch on ``type_`` and ``name``, so ``object`` is the
    honest annotation — nothing narrower is true.
    """
    del reflected, compare_to
    if type_ == "table":
        return name not in AUTH_TABLES
    return True


# Set when alembic runs; the invariant in scripts/checks/invariants.sh greps for
# `include_object=include_object` to confirm the wiring survived.
include_object = include_object


def run_migrations_offline() -> None:
    raise NotImplementedError("No database in v1 — migrations arrive with the DB (v3).")


def run_migrations_online() -> None:
    raise NotImplementedError("No database in v1 — migrations arrive with the DB (v3).")
