"""The kill switch — "a config flag and a check, not a system"
(infrastructure.md:124). A global spend ceiling that halts spend fails safe
regardless of how it was reached.

The flag is the KILL_SWITCH env var ("1" = tripped). It is checked at the
same fail-closed spend point as the quota (consume_quota); when tripped,
spend refuses even if the quota has room.

ponytail: an env flag is the documented "config flag"; a DB-backed global
switch lands when there is ops tooling to flip it without a deploy.
"""

from __future__ import annotations

import os


def kill_switch_tripped() -> bool:
    """True when spend is halted globally."""
    return os.environ.get("KILL_SWITCH") == "1"


def forced_plan() -> str | None:
    """The plan FORCE_PLAN pins the instance to, or ``None`` when the account's
    own row decides.

    ``None`` is not "free". It means the row is authoritative — which is what a
    future Stripe webhook writes, and the reason this cannot default to a plan:
    returning "free" here made a paid row unreachable, so no account could ever
    be paid and every paid capability was dead (brand kits included).

    When it is set, the data layer writes it through to the row, so the plan's
    limit follows the flip instead of the row keeping the old one.
    """
    forced = os.environ.get("FORCE_PLAN")
    return forced if forced in ("free", "paid") else None
