"""SQLAlchemy, the only place `experiences` rows are touched. Every call takes
an `AsyncSession` from `as_user()` — the RLS policy on the table is the actual
enforcement, this module never adds its own `owner_id = ...` filter, so a
row that RLS would hide is never visible here either.

Owns the service-role filter for reads that must only ever see published
content (`published_at is not null`) — nothing calls it from an anonymous
context yet in v1 (serving is a static file, not a query), but the pattern
exists now so it is not retrofitted later (docs/coderules/patterns.md rule 3).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Experience


async def find_by_id(session: AsyncSession, experience_id: UUID) -> Experience | None:
    return await session.get(Experience, experience_id)


async def find_published_by_id(
    session: AsyncSession, experience_id: UUID
) -> Experience | None:
    stmt = select(Experience).where(
        Experience.id == experience_id, Experience.published_at.is_not(None)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create(
    session: AsyncSession,
    *,
    owner_id: UUID,
    experience_id: UUID | None,
    title: str,
    mode: str,
    brand_id: str | None,
    art_direction: str,
    scenes: list[dict[str, object]],
) -> Experience:
    """`experience_id` is the caller's proposal, and `None` means "you pick" —
    the column's `gen_random_uuid()` default then applies, which is why it is
    omitted from the kwargs rather than passed as `None` (that would insert a
    literal NULL into a primary key).

    Why a caller may propose one at all: `/new` mints a UUID before Intake and
    every `generations` row for that session — Intake's, the Director's, Build's
    eight — is written against it. If the finished experience then got a fresh
    server id, `generations.experience_id` would point at nothing and the log
    could never answer the one question it exists to answer, which is what an
    experience cost to make.

    ponytail: this is safe while there is one user. With real tenants, an id a
    client proposes is an existence oracle — insert succeeds or hits a unique
    violation — so this becomes server-generated again and the build session
    gets its own column. Trigger: the first non-local user.
    """
    row = Experience(
        **({} if experience_id is None else {"id": experience_id}),
        owner_id=owner_id,
        title=title,
        mode=mode,
        brand_id=brand_id,
        art_direction=art_direction,
        scenes=scenes,
    )
    session.add(row)
    await session.flush()
    return row


async def replace(
    session: AsyncSession,
    row: Experience,
    *,
    title: str,
    mode: str,
    brand_id: str | None,
    art_direction: str,
    scenes: list[dict[str, object]],
) -> Experience:
    """A full replace, not a patch — `BlockPatch` (one block, editor-scoped) is
    a different shape for a different phase (09). This is publish's own
    "republish after an edit" verification step, not the property panel."""
    row.title = title
    row.mode = mode
    row.brand_id = brand_id
    row.art_direction = art_direction
    row.scenes = scenes
    await session.flush()
    return row


async def set_published(
    session: AsyncSession, row: Experience, at: datetime
) -> Experience:
    row.published_at = at
    await session.flush()
    return row


async def unpublish(session: AsyncSession, row: Experience) -> Experience:
    row.published_at = None
    await session.flush()
    return row
