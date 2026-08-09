"""Publish's public surface. Every function here takes the caller's user id
(v1: always `config().local_user_id` — the wrapper does not know the
difference between that and a real session, which is the point) and goes
through `as_user()`. Nothing outside this module touches `publish_data.py`
or the ORM.
"""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from db.models import Experience as ExperienceRow
from db.tenant import as_user
from features.publish import publish_data
from lib.result import Result, err, ok
from schema.experience import ArtDirectionId, Experience, ExperienceMeta
from schema.scene import Mode


def _to_schema(row: ExperienceRow) -> Experience:
    if row.brand_id is None:
        raise ValueError(
            "brand_id is only ever null for a row this feature didn't create"
        )
    return Experience(
        id=str(row.id),
        title=row.title,
        mode=cast(Mode, row.mode),
        brand_id=row.brand_id,
        art_direction=cast(ArtDirectionId, row.art_direction),
        scenes=row.scenes,  # type: ignore[arg-type]  # validated on the way in; re-validated here on the way out
        meta=ExperienceMeta(
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
            published_at=row.published_at.isoformat() if row.published_at else None,
        ),
    )


def _proposed_id(experience_id: str) -> UUID | None:
    """The caller's id if it is a well-formed UUID, otherwise `None` — meaning
    the server picks one.

    Not a validation error, because the fixtures this feature is tested against
    carry human ids ("exp-full", "exp-minimal") and always have. The rule is
    "an id we can honour, we honour"; the shape of `Experience.id` is `str`, so
    anything else is a name the database has no column for. See
    `publish_data.create` for why a caller proposes one at all."""
    try:
        return UUID(experience_id)
    except ValueError:
        return None


async def create_experience(user_id: str, experience: Experience) -> Result[Experience]:
    async with as_user(user_id) as session:
        row = await publish_data.create(
            session,
            owner_id=UUID(user_id),
            experience_id=_proposed_id(experience.id),
            title=experience.title,
            mode=experience.mode,
            brand_id=experience.brand_id,
            art_direction=experience.art_direction,
            scenes=[s.model_dump(by_alias=True) for s in experience.scenes],
        )
        return ok(_to_schema(row))


async def get_experience(user_id: str, experience_id: str) -> Result[Experience]:
    try:
        parsed_id = UUID(experience_id)
    except ValueError:
        return err("not_found", experience_id)
    async with as_user(user_id) as session:
        row = await publish_data.find_by_id(session, parsed_id)
        if row is None:
            return err("not_found", experience_id)
        return ok(_to_schema(row))


async def replace_experience(
    user_id: str, experience_id: str, experience: Experience
) -> Result[Experience]:
    try:
        parsed_id = UUID(experience_id)
    except ValueError:
        return err("not_found", experience_id)
    async with as_user(user_id) as session:
        row = await publish_data.find_by_id(session, parsed_id)
        if row is None:
            return err("not_found", experience_id)
        row = await publish_data.replace(
            session,
            row,
            title=experience.title,
            mode=experience.mode,
            brand_id=experience.brand_id,
            art_direction=experience.art_direction,
            scenes=[s.model_dump(by_alias=True) for s in experience.scenes],
        )
        return ok(_to_schema(row))


async def publish_experience(user_id: str, experience_id: str) -> Result[Experience]:
    """Republishing is explicit, not automatic — this is the one call a
    caller makes to say "ship what's there right now." It never touches
    content; an edit is `replace_experience`, called first."""
    try:
        parsed_id = UUID(experience_id)
    except ValueError:
        return err("not_found", experience_id)
    async with as_user(user_id) as session:
        row = await publish_data.find_by_id(session, parsed_id)
        if row is None:
            return err("not_found", experience_id)
        row = await publish_data.set_published(session, row, datetime.now(UTC))
        return ok(_to_schema(row))


async def unpublish_experience(user_id: str, experience_id: str) -> Result[Experience]:
    try:
        parsed_id = UUID(experience_id)
    except ValueError:
        return err("not_found", experience_id)
    async with as_user(user_id) as session:
        row = await publish_data.find_by_id(session, parsed_id)
        if row is None:
            return err("not_found", experience_id)
        row = await publish_data.unpublish(session, row)
        return ok(_to_schema(row))
