"""FastAPI auth dependency — resolves the session, failing closed.

web issues the session (Better Auth); api resolves it read-only (the
documented exception to table ownership) and injects the user_id. A missing
or invalid session denies the request with 401 — there is no permissive
default (OWASP A10, patterns.md rule 5).

The token comes from the `Authorization: Bearer <token>` header. (The Better
Auth cookie name is web's concern; api accepts the explicit token.)

Authorization is checked here AND the tenant scope is applied via as_user in
the route — the data layer, never middleware alone (security README, CVE-
2025-29927). This dependency is the 401 gate; RLS is the isolation.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from auth.session_data import resolve_session
from lib.result import Err

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="unauthorized",
)


async def current_user_id(
    authorization: str | None = Header(default=None),
) -> str:
    """Dependency: extract and resolve the session token -> user_id.

    Fails closed: a missing header, a missing row, an expired session, or an
    unreadable database all deny. Never a default user, never a grant.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise _UNAUTHORIZED
    token = authorization.removeprefix("Bearer ").strip()
    result = await resolve_session(token)
    if isinstance(result, Err):
        raise _UNAUTHORIZED
    return result.value
