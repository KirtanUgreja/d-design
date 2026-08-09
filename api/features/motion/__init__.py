"""Motion's public surface. Nothing outside this module touches
`motion_data.py`, `seed.py` or the ORM (rule 4).

Resolution fails closed, like the art direction's: an experience naming a
vocabulary that does not exist is `not_found`, and the page renders its designed
empty state rather than a scene tree with no timings at all.
"""

from db.tenant import as_user
from features.motion import motion_data
from lib.result import Result, err, ok
from schema.motion import MotionVocabularyRecord, MotionVocabularyRef


async def load_motion(
    user_id: str, ref: MotionVocabularyRef
) -> Result[MotionVocabularyRecord]:
    async with as_user(user_id) as session:
        record = await motion_data.find(session, ref.id)
    if record is None:
        return err("not_found", ref.id)
    return ok(record)


async def list_motion_vocabularies(user_id: str) -> list[MotionVocabularyRecord]:
    """No `Result`: "there are none" is a legitimate answer with a designed
    empty state, and a caller that cannot reach the database has already failed
    at `as_user`."""
    async with as_user(user_id) as session:
        return await motion_data.list_latest(session)


__all__ = ["list_motion_vocabularies", "load_motion"]
