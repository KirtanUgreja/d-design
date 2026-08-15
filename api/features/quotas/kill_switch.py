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


def effective_plan() -> str:
    """The plan for the whole instance. FORCE_PLAN overrides per-row plans
    (the static/testing knob; a future Stripe webhook flips the per-row plan
    instead). Free is the default — never a permissive upgrade."""
    forced = os.environ.get("FORCE_PLAN")
    if forced in ("free", "paid"):
        return forced
    return "free"
