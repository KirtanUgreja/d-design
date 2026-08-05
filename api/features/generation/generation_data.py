"""SQLAlchemy for `quotas` and `generations` — homed here because `generation`
(the Build phase) is the first, and in v1 the only, caller of the model seam.
Future phases (intake, director, edit) import `consume_quota`/
`record_generation` from this feature's public surface too, the same way any
cross-feature access happens (docs/coderules/structure.md).
"""

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Generation, Quota


async def consume_quota(session: AsyncSession, owner_id: UUID) -> bool:
    """Atomic increment — one statement, so there is no window between the
    check and the consumption (docs/techstack/backend.md). True if a row came
    back: quota available and not halted. False covers both "exhausted" and
    "halted" on purpose — the caller fails closed either way and does not
    need to tell them apart to do it correctly (patterns.md rule 5)."""
    stmt = (
        update(Quota)
        .where(
            Quota.owner_id == owner_id,
            Quota.used < Quota.limit,
            Quota.halted.is_(False),
        )
        .values(used=Quota.used + 1)
        .returning(Quota.used)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def record_generation(
    session: AsyncSession,
    *,
    owner_id: UUID,
    experience_id: UUID,
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
    """Metadata only. No prompt, no output, no brief content — ever
    (docs/v1/ai-pipeline.md -> "generations")."""
    session.add(
        Generation(
            owner_id=owner_id,
            experience_id=experience_id,
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
    )
    await session.flush()
