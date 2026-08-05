"""SQLAlchemy for `briefs`. The ORM lives in a feature data module and
nowhere else (docs/coderules/patterns.md rule 8).

The brief is **stored and never logged**. It is the customer's unreleased
launch messaging, and the difference between a row in a table they own and a
line in an error tracker is the whole of docs/security/tenancy-and-data.md.
`test_privacy.py` sends a canary string through this path and greps everywhere
else for it.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import BriefRow
from schema.brief import Brief


async def save_brief(
    session: AsyncSession, *, owner_id: UUID, experience_id: UUID, brief: Brief
) -> None:
    """`by_alias=True` so what lands in `jsonb` is the same camelCase shape
    `web` and every other reader of a `Brief` sees — the row is the contract,
    not a Python-shaped private encoding of it."""
    session.add(
        BriefRow(
            owner_id=owner_id,
            experience_id=experience_id,
            payload=brief.model_dump(by_alias=True),
        )
    )


async def load_brief(session: AsyncSession, *, experience_id: UUID) -> Brief | None:
    """No `owner_id` filter, and that is not an oversight: every caller reaches
    this through `as_user`, so the RLS policy on `briefs` is what scopes the
    read. A second filter in Python would imply the policy is optional
    (docs/coderules/patterns.md rule 9).

    Newest wins — the interview can be re-run, and re-running it is how a user
    corrects a brief.
    """
    row = (
        await session.execute(
            select(BriefRow)
            .where(BriefRow.experience_id == experience_id)
            .order_by(BriefRow.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return None if row is None else Brief.model_validate(row.payload)
