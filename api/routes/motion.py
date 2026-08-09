"""Motion vocabularies: read, and only read.

No POST, for the same reason `routes/art_directions.py` has none and a stronger
one: `motion_vocabularies` has no `owner_id` column at all, so there is no such
thing as a user-authored vocabulary to write. Every row is a system row seeded
by migration.

`web` and `render` both consume what this serves — `render` holds no credential
and cannot read the store, so its payload carries the vocabulary and it parses
it with the same generated validator.
"""

from fastapi import APIRouter

from config import config
from features.motion import list_motion_vocabularies, load_motion
from lib.result import AppError, Err
from routes.errors import as_http_exception
from schema.motion import MotionVocabularyRecord, MotionVocabularyRef

router = APIRouter(prefix="/motion-vocabularies", tags=["motion"])


@router.get("")
async def index() -> list[MotionVocabularyRecord]:
    return await list_motion_vocabularies(config().local_user_id)


@router.get("/{vocabulary_id}")
async def read(vocabulary_id: str) -> MotionVocabularyRecord:
    """The newest version, and there is no version in the path.

    The asymmetry with `/art-directions/{id}/{version}` is the point. An art
    direction is user-editable, so a page pinned to one has to name a version
    or it restyles itself when its author edits it. A motion vocabulary is a
    system row whose new version is a migration — deliberate, reviewed, and
    frozen into a published artifact regardless.
    """
    try:
        ref = MotionVocabularyRef(id=vocabulary_id)
    except ValueError:
        # A malformed id is indistinguishable from one that does not exist;
        # answering differently would confirm which ids are well-formed.
        raise as_http_exception(AppError("not_found", vocabulary_id)) from None

    result = await load_motion(config().local_user_id, ref)
    if isinstance(result, Err):
        raise as_http_exception(result.error)
    return result.value
