"""Art directions: read, and only read.

There is no POST. System art directions are seeded by migration because the
write policy on the table has no `owner_id is null` arm (see 0008), and user
authoring is late v2 at the earliest. A write route that exists before the
feature does is an attack surface with no user.

`web` and `render` both consume what this serves. `web` fetches a record and
turns it into tokens; `render` holds no credential and cannot read the store at
all, so its payload carries the record and it parses it with the same generated
validator. One shape, two consumers, one place it is defined.
"""

from fastapi import APIRouter

from config import config
from features.art_direction import list_art_directions, load_art_direction
from lib.result import AppError, Err
from routes.errors import as_http_exception
from schema.art_direction import ArtDirectionRecord, ArtDirectionRef

router = APIRouter(prefix="/art-directions", tags=["art-directions"])


@router.get("")
async def index() -> list[ArtDirectionRecord]:
    """The newest version of each — what a picker offers. Older versions stay
    readable by reference; they are just not on the menu."""
    return await list_art_directions(config().local_user_id)


@router.get("/{art_direction_id}/{version}")
async def read(art_direction_id: str, version: int) -> ArtDirectionRecord:
    """`{id, version}`, both required.

    The path could have defaulted the version to "latest" and it deliberately
    does not: every caller that omitted it would be a page that restyles itself
    when a new version lands, which is exactly the rule the version exists to
    keep (v2 rule 15).
    """
    try:
        ref = ArtDirectionRef(id=art_direction_id, version=version)
    except ValueError:
        # A malformed id is indistinguishable from an id that does not exist,
        # and answering differently would confirm which ids are well-formed.
        raise as_http_exception(AppError("not_found", art_direction_id)) from None

    result = await load_art_direction(config().local_user_id, ref)
    if isinstance(result, Err):
        raise as_http_exception(result.error)
    return result.value
