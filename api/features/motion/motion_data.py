"""SQLAlchemy for `motion_vocabularies`. The ORM lives in a feature data module
and nowhere else (docs/coderules/patterns.md rule 8).

The table has no `owner_id` and its policy is `using (true)` for select and
nothing else — every row is a system row, readable by everyone, writable by the
migration role alone. So there is no `save` here, and the absence is the
feature rather than a gap: user-authored motion is not a v2 feature.

`find` takes an id and returns the newest version, which is the one asymmetry
with `art_direction_data.find` and is deliberate. See `MotionVocabularyRef`.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import MotionVocabulary
from schema.motion import MotionVocabularyRecord


async def find(
    session: AsyncSession, vocabulary_id: str
) -> MotionVocabularyRecord | None:
    """The newest version of one vocabulary.

    Newest rather than pinned, unlike an art direction. A pinned reference
    exists to stop a *user's edit* silently restyling a page they published; a
    new version of a system motion vocabulary is a migration, deliberate and
    reviewed, and a published page has the resolved vocabulary frozen into its
    artifact regardless. Two mechanisms for one guarantee would be one too many.
    """
    row = (
        await session.execute(
            select(MotionVocabulary)
            .where(MotionVocabulary.id == vocabulary_id)
            .order_by(MotionVocabulary.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return None if row is None else _as_record(row)


async def list_latest(session: AsyncSession) -> list[MotionVocabularyRecord]:
    """The newest version of each — what a picker offers, when there is one.
    Ordered by id so the list is stable between requests."""
    rows = (
        (
            await session.execute(
                select(MotionVocabulary).order_by(
                    MotionVocabulary.id, MotionVocabulary.version.desc()
                )
            )
        )
        .scalars()
        .all()
    )
    latest: dict[str, MotionVocabulary] = {}
    for row in rows:
        latest.setdefault(row.id, row)
    return [_as_record(row) for row in latest.values()]


def _as_record(row: MotionVocabulary) -> MotionVocabularyRecord:
    """Parsed on the way out, not trusted — the column is `jsonb` and Postgres
    does not know what shape it holds, so a row written by an older migration is
    external input by the time it reaches Python."""
    return MotionVocabularyRecord.model_validate(
        {"id": row.id, "version": row.version, **row.tokens}
    )
