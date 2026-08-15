"""quotas data access — the atomic counter (phase 19).

backend.md:160-174: the quota check is an atomic increment, not read-then-
write — concurrent requests reading the same balance and all proceeding is
the A10 race. One statement (`limit` is quoted — it is a reserved word in Postgres):

    update quotas set used = used + 1
    where account_id = :acc and used < "limit"
    returning used;

No row returned means refused. The check and the consumption are the same
operation, so there is no window between them.

Every call runs inside the caller's as_user transaction — the same one as the
action that spends the quota, so a refused check rolls the action back too.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

FREE_LIMIT = 1
PAID_LIMIT = 50  # a config number, deliberately generous (decisions.md: the
# numbers are not chosen; this is the enforcement default)


@dataclass(frozen=True)
class QuotaExceeded:
    """The spend was refused — the atomic counter returned no row."""

    used: int
    limit: int


@dataclass(frozen=True)
class Entitlement:
    plan: str
    used: int
    limit: int

    @property
    def exhausted(self) -> bool:
        return self.used >= self.limit


def plan_limit(plan: str) -> int:
    """The hosted-URL limit for a plan. Free: 1. Paid: the config number."""
    return FREE_LIMIT if plan == "free" else PAID_LIMIT


async def ensure_quota_row(
    session: AsyncSession, account_id: str, *, plan: str, limit: int
) -> None:
    """Create the account's quota row if absent. `on conflict do nothing`
    keeps concurrent first-publishes from racing on the insert."""
    await session.execute(
        text(
            'insert into quotas (account_id, plan, used, "limit")'
            " values (:acc, :plan, 0, :limit)"
            " on conflict (account_id) do nothing"
        ),
        {"acc": account_id, "plan": plan, "limit": limit},
    )


async def consume_quota(
    session: AsyncSession,
    account_id: str,
    *,
    plan: str,
    limit: int,
) -> QuotaExceeded | None:
    """Atomically consume one unit of the account's quota.

    Returns None when the spend succeeded (a row was returned), or the
    refusal (used/limit) when the counter was already at the limit.
    Fail-closed: any exception here propagates — a quota check that cannot
    run refuses (AGENTS.md rule 10).
    """
    await ensure_quota_row(session, account_id, plan=plan, limit=limit)
    row = (
        await session.execute(
            text(
                "update quotas set used = used + 1, updated_at = now()"
                ' where account_id = :acc and used < "limit"'
                ' returning used, "limit"'
            ),
            {"acc": account_id},
        )
    ).first()
    if row is None:
        # Read the current state for the refusal detail (still atomic enough:
        # the update already refused; this is diagnostics).
        current = (
            await session.execute(
                text('select used, "limit" from quotas where account_id = :acc'),
                {"acc": account_id},
            )
        ).first()
        if current is not None:
            return QuotaExceeded(used=current[0], limit=current[1])
        return QuotaExceeded(used=0, limit=limit)
    return None


async def get_entitlement(session: AsyncSession, account_id: str, *, plan: str) -> Entitlement:
    """The account's current entitlement (plan, used, limit). Creates the
    default free row if the account has never spent."""
    limit = plan_limit(plan)
    await ensure_quota_row(session, account_id, plan=plan, limit=limit)
    row = (
        await session.execute(
            text('select plan, used, "limit" from quotas where account_id = :acc'),
            {"acc": account_id},
        )
    ).first()
    if row is None:
        # ensure_quota_row just created the row; a missing row here is a bug,
        # and failing closed (never fabricating an entitlement) is the safe
        # answer either way.
        raise RuntimeError("quota row missing after ensure")
    return Entitlement(plan=row[0], used=row[1], limit=row[2])
