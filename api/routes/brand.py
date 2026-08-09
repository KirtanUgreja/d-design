"""The brand kit: read and save.

`BrandKit` parses at entry like every other body, which is what makes "a font
can only be selected by registry id" true of the API and not only of the UI —
`display_font` is a `Literal`, so a raw family string is a 422 before this
function runs.
"""

from uuid import UUID

from fastapi import APIRouter

from config import config
from db.tenant import as_user
from features.brand import load_brand, save_brand
from lib.result import AppError
from routes.errors import as_http_exception
from schema.experience import BrandKit

router = APIRouter(prefix="/brand", tags=["brand"])


@router.get("")
async def read() -> BrandKit:
    async with as_user(config().local_user_id) as session:
        kit = await load_brand(session)
    if kit is None:
        # Not an empty default. The brand kit is asked for *second*, after the
        # first artifact exists, so "there isn't one yet" is the normal state
        # for a new user and the client has to be able to tell.
        raise as_http_exception(AppError("not_found", "no brand kit yet"))
    return kit


@router.put("")
async def replace(body: BrandKit) -> BrandKit:
    owner_id = config().local_user_id
    async with as_user(owner_id) as session:
        return await save_brand(session, owner_id=UUID(owner_id), kit=body)
