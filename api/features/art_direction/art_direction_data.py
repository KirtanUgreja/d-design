"""SQLAlchemy for `art_directions`. The ORM lives in a feature data module and
nowhere else (docs/coderules/patterns.md rule 8).

Every call takes an `AsyncSession` from `as_user()`. This module adds no
`owner_id` filter of its own — the read policy on the table is what makes a
system art direction visible to everyone and a user's own visible to them, and
re-stating it here would be a second copy of a rule that must have exactly one.

There is no `save`. System rows are seeded by migration, because the write
policy deliberately has no `owner_id is null` arm: a tenant that could insert
one could publish an art direction to every other account on the platform. User
authoring is late v2 and gets its own insert path, with `owner_id` set.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ArtDirection
from schema.art_direction import ArtDirectionRecord, ArtDirectionRef


async def find(
    session: AsyncSession, ref: ArtDirectionRef
) -> ArtDirectionRecord | None:
    """One version of one art direction, or nothing.

    Both halves of the key are in the `where`. Looking up by id alone and
    taking the newest would make an experience pinned to version 1 restyle
    itself the moment version 2 landed — which is precisely v2 rule 15's
    failure mode, and it would arrive as a convenience.
    """
    row = (
        await session.execute(
            select(ArtDirection).where(
                ArtDirection.id == ref.id, ArtDirection.version == ref.version
            )
        )
    ).scalar_one_or_none()
    return None if row is None else _as_record(row)


async def list_latest(session: AsyncSession) -> list[ArtDirectionRecord]:
    """The newest version of each art direction the caller can see — what a
    picker offers. Ordered by id so the list is stable between requests; a
    picker whose rows move is a picker people misclick."""
    rows = (
        (
            await session.execute(
                select(ArtDirection).order_by(
                    ArtDirection.id, ArtDirection.version.desc()
                )
            )
        )
        .scalars()
        .all()
    )
    latest: dict[str, ArtDirection] = {}
    for row in rows:
        latest.setdefault(row.id, row)
    return [_as_record(row) for row in latest.values()]


def _as_record(row: ArtDirection) -> ArtDirectionRecord:
    """Parsed on the way out, not trusted.

    The columns are `jsonb` and Postgres does not know what shape they hold, so
    a row written by an older migration — or by hand during an incident — is
    external input by the time it reaches Python. A `ValidationError` here is
    loud, which is the right outcome: a half-understood art direction rendering
    as a partly-styled page is the failure this parse exists to prevent.
    """
    return ArtDirectionRecord.model_validate(
        {
            "id": row.id,
            "version": row.version,
            "name": row.name,
            "author": row.author,
            "tokens": row.tokens,
            "extensions": {
                "budgets": row.budgets,
                "brandMapping": row.brand_mapping,
                "defaultMotion": row.default_motion,
                "fluid": row.fluid,
            },
        }
    )
