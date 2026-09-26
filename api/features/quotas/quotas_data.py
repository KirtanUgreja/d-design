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

DEFAULT_PLAN = "free"

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


async def ensure_quota_row(session: AsyncSession, account_id: str, *, forced: str | None) -> None:
    """Create the account's quota row if absent; when the instance is pinned by
    FORCE_PLAN, write the pinned plan through.

    The write-through matters. `on conflict do nothing` left an existing row's
    plan and limit exactly as they were, so once an account had a row the
    override could never take effect — and since every first request creates
    one, that was every account. The knob is documented as flipping the
    instance; this is the line that makes it true.

    With ``forced`` None the conflict clause skips the update and the row is
    authoritative, which is what a Stripe webhook will write.
    """
    plan = forced if forced is not None else DEFAULT_PLAN
    await session.execute(
        text(
            'insert into quotas (account_id, plan, used, "limit")'
            " values (:acc, :plan, 0, :limit)"
            " on conflict (account_id) do update"
            ' set plan = excluded.plan, "limit" = excluded."limit", updated_at = now()'
            " where :overriding"
        ),
        {
            "acc": account_id,
            "plan": plan,
            "limit": plan_limit(plan),
            "overriding": forced is not None,
        },
    )


async def consume_quota(
    session: AsyncSession,
    account_id: str,
    *,
    forced: str | None,
) -> QuotaExceeded | None:
    """Atomically consume one unit of the account's quota.

    Returns None when the spend succeeded (a row was returned), or the
    refusal (used/limit) when the counter was already at the limit.
    Fail-closed: any exception here propagates — a quota check that cannot
    run refuses (AGENTS.md rule 10).

    The limit comes from the plan rather than the caller: the plan decides the
    limit, so passing both invited them to disagree.
    """
    await ensure_quota_row(session, account_id, forced=forced)
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
        return QuotaExceeded(used=0, limit=plan_limit(forced or DEFAULT_PLAN))
    return None


async def get_entitlement(
    session: AsyncSession, account_id: str, *, forced: str | None
) -> Entitlement:
    """The account's current entitlement (plan, used, limit). Creates the
    default free row if the account has never spent.

    Reads back from the row rather than echoing the plan it was handed, so the
    two can only disagree if the database does — and the row is what the spend
    gate checks against.
    """
    await ensure_quota_row(session, account_id, forced=forced)
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
