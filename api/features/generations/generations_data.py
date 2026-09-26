"""generations data access — per-stage telemetry (v3).

`backend.md:214` draws the line this table exists to hold: **"No prompts. No
outputs. No brief content."** One row per stage request, carrying the phase, the
model, whether the seam had to repair, and how long it took. Enough to answer
what a deck costs and which stage fails most; deliberately not enough to
reconstruct what anyone asked for or what they got.

`experience_id` is left null. A generation happens before any deck row exists,
so linking them would mean threading a draft id through three separate requests
— more machinery than the number is worth. The phase/model/latency data stands
on its own.

Token counts and money are not here. `CallStats` counts calls and latency, not
tokens, so per-deck currency needs token accounting in the seam first; this is
the shape that makes it a column rather than a redesign.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def record_generation(
    session: AsyncSession,
    *,
    phase: str,
    model: str,
    repair: bool,
    latency_ms: int,
) -> None:
    """Record one stage's metadata. `owner_id` comes from `app.user_id`.

    Note what is absent: the brief, the prompt, the model's output, the deck.
    Adding any of them to this insert would be the tenancy-and-data rule broken
    at the one place designed to obey it.
    """
    await session.execute(
        text(
            "insert into generations (id, owner_id, phase, model, repair, latency_ms)"
            " values (:id, current_setting('app.user_id')::uuid, :phase, :model, :repair,"
            " :latency)"
        ),
        {
            "id": str(uuid.uuid4()),
            "phase": phase,
            "model": model,
            "repair": repair,
            "latency": latency_ms,
        },
    )
