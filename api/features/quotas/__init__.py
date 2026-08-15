"""quotas feature — the billing spine (phase 19).

The public surface: consume_quota (the atomic, transactional spend gate),
get_entitlement (what web asks before rendering), and the kill switch that
bounds denial-of-wallet.

Stripe is deliberately deferred (user decision): the per-row `plan` column is
the future webhook slot; FORCE_PLAN is the static/testing knob today.
"""

from features.quotas.kill_switch import effective_plan, kill_switch_tripped
from features.quotas.quotas_data import (
    Entitlement,
    QuotaExceeded,
    consume_quota,
    get_entitlement,
    plan_limit,
)

__all__ = [
    "Entitlement",
    "QuotaExceeded",
    "consume_quota",
    "effective_plan",
    "get_entitlement",
    "kill_switch_tripped",
    "plan_limit",
]
