"""Art direction's public surface. Nothing outside this module touches
`art_direction_data.py`, `dtcg.py` or the ORM (rule 4).

The one thing to understand before reading a caller: **resolution fails
closed.** v1's resolver was `Record<ArtDirectionId, …>` in TypeScript, so a
missing art direction was a compile error. That property cannot survive a
database read, and pretending otherwise is worse than losing it deliberately —
so an unknown `{id, version}` is `not_found`, and the page that asked renders
its designed empty state rather than a scene tree with no tokens at all.
"""

from db.tenant import as_user
from features.art_direction import art_direction_data
from features.art_direction.dtcg import from_document, to_document
from features.art_direction.lint import lint_art_direction, lint_motion_vocabulary
from lib.result import Result, err, ok
from schema.art_direction import ArtDirectionRecord, ArtDirectionRef


async def load_art_direction(
    user_id: str, ref: ArtDirectionRef
) -> Result[ArtDirectionRecord]:
    async with as_user(user_id) as session:
        record = await art_direction_data.find(session, ref)
    if record is None:
        return err("not_found", f"{ref.id} v{ref.version}")
    return ok(record)


async def list_art_directions(user_id: str) -> list[ArtDirectionRecord]:
    """No `Result`: "there are none" is a legitimate answer with a designed
    empty state, and a caller that cannot reach the database has already
    failed at `as_user`."""
    async with as_user(user_id) as session:
        return await art_direction_data.list_latest(session)


__all__ = [
    "from_document",
    "lint_art_direction",
    "lint_motion_vocabulary",
    "list_art_directions",
    "load_art_direction",
    "to_document",
]
