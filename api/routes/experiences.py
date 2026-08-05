"""Routes are thin: parse input, call the feature, return the result.

v1 has one user (docs/v1/spec.md -> "No auth in local v1"), so every call
uses `config().local_user_id` — the same argument `as_user()` will take from
a real session in v3, which is the entire point of building the wrapper now.
"""

from fastapi import APIRouter

from config import config
from features.publish import (
    create_experience,
    get_experience,
    publish_experience,
    replace_experience,
    unpublish_experience,
)
from lib.result import Err, Result
from routes.errors import as_http_exception
from schema.experience import Experience

router = APIRouter(prefix="/experiences", tags=["experiences"])


def _unwrap(result: Result[Experience]) -> Experience:
    if isinstance(result, Err):
        raise as_http_exception(result.error)
    return result.value


@router.post("", status_code=201)
async def create(body: Experience) -> Experience:
    return _unwrap(await create_experience(config().local_user_id, body))


@router.get("/{experience_id}")
async def read(experience_id: str) -> Experience:
    return _unwrap(await get_experience(config().local_user_id, experience_id))


@router.put("/{experience_id}")
async def replace(experience_id: str, body: Experience) -> Experience:
    return _unwrap(
        await replace_experience(config().local_user_id, experience_id, body)
    )


@router.post("/{experience_id}/publish")
async def publish(experience_id: str) -> Experience:
    return _unwrap(await publish_experience(config().local_user_id, experience_id))


@router.post("/{experience_id}/unpublish")
async def unpublish(experience_id: str) -> Experience:
    return _unwrap(await unpublish_experience(config().local_user_id, experience_id))
