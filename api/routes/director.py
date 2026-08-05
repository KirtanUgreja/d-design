"""Non-streaming: Director makes exactly one call and returns exactly one
`Outline` (docs/v1/plan/07-director.md -> "The call"). No SSE needed —
Build's stream exists because it has many scenes to reveal one at a time;
Director has one thing to return, and the client's job is to render it as
an editable gate (the outline-editor), not watch it arrive.
"""

from fastapi import APIRouter

from config import config
from features.director import direct_brief
from lib.result import Err, Result
from routes.errors import as_http_exception
from schema.base import Schema
from schema.brief import Brief
from schema.outline import Outline

router = APIRouter(prefix="/experiences", tags=["director"])


class DirectorRequest(Schema):
    brief: Brief


def _unwrap(result: Result[Outline]) -> Outline:
    if isinstance(result, Err):
        raise as_http_exception(result.error)
    return result.value


@router.post("/{experience_id}/director")
async def direct(experience_id: str, body: DirectorRequest) -> Outline:
    return _unwrap(
        await direct_brief(
            brief=body.brief,
            owner_id=config().local_user_id,
            experience_id=experience_id,
        )
    )
