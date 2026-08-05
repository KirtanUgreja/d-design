"""Quota + kill-switch check and generation logging — split out from this
package's `__init__.py` so `ai/complete.py` can import them directly
(docs/v1/plan/06-model-seam-and-build.md). The seam needs these before
`build_experience` exists, and importing through `features.generation` itself
would round-trip back through a package `__init__` that is still mid-import
when the seam is what triggered it — the same circular-import shape
`build.py` avoids by importing `checks`/`tools` directly rather than through
the package.
"""

from uuid import UUID

from db.tenant import as_user
from features.generation import generation_data
from lib.result import Result, err, ok


async def check_quota_and_kill_switch(owner_id: str) -> Result[None]:
    """Checked before every model call, atomically, failing closed
    (patterns.md rule 5). Anything that prevents the check from completing —
    a connection error, a timeout — is treated exactly like "over quota":
    refused, not permitted. There is no permissive branch to fall into."""
    try:
        async with as_user(owner_id) as session:
            available = await generation_data.consume_quota(session, UUID(owner_id))
    except Exception as e:  # fails closed on purpose: an unreadable quota service must refuse, not permit (rule 5)
        return err("quota_exceeded", f"quota check unavailable: {type(e).__name__}")
    if not available:
        return err("quota_exceeded", "quota exhausted or generation halted")
    return ok(None)


async def log_generation(
    *,
    owner_id: str,
    experience_id: str,
    phase: str,
    model_id: str,
    provider_route: str,
    tokens_in: int,
    tokens_out: int,
    cached_tokens: int,
    calls: int,
    repaired: bool,
    error_class: str | None,
    duration_ms: int,
) -> None:
    async with as_user(owner_id) as session:
        await generation_data.record_generation(
            session,
            owner_id=UUID(owner_id),
            experience_id=UUID(experience_id),
            phase=phase,
            model_id=model_id,
            provider_route=provider_route,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cached_tokens=cached_tokens,
            calls=calls,
            repaired=repaired,
            error_class=error_class,
            duration_ms=duration_ms,
        )
