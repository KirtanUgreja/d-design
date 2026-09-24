"""Database error classification — the expected-refusal seam.

An RLS policy's ``with check`` refusing a write is an *expected* authorization
failure: the caller is writing to a team it is not a member of. Postgres
reports it as SQLSTATE 42501 (insufficient_privilege). Classifying it here lets
a data module return ``Result``/``Err`` and the route answer 403, instead of
letting a bare 500 escape from a refusal the architecture planned for
(python.md: expected failures return a Result; only bugs raise).

Deliberately structural — the SQLSTATE, not the driver's exception class — so
the classification survives a driver swap.
"""

from __future__ import annotations

from sqlalchemy.exc import DBAPIError

# insufficient_privilege: what a row-level security policy's with-check raises
# when it refuses a row.
_RLS_REFUSAL = "42501"


def is_rls_refusal(exc: DBAPIError) -> bool:
    """True when ``exc`` is the database refusing a row because of an RLS policy."""
    return getattr(exc.orig, "sqlstate", None) == _RLS_REFUSAL
