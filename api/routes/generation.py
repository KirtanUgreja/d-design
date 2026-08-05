"""SSE endpoint for the Build phase — one validated scene per event, streamed
as it completes (docs/v1/plan/06-model-seam-and-build.md -> "7. Streaming to
the client"). `experience_id` is caller-supplied and not looked up: Build
writes nothing to `experiences` (it only logs to `generations`, which is
`owner_id`-scoped), so the id exists purely for that log's FK until the
client assembles the finished scenes into an `Experience` and creates it
through `routes/experiences.py`.

Not a literal `EventSource` on the client: `EventSource` is GET-only and this
call needs a JSON body (`brief`, `outline`), so the client reads the same
`text/event-stream` wire format by hand instead (web/src/features/generation).
"""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from config import config
from features.director import approve_outline
from features.generation.build import BuildEvent, build_experience
from lib.result import Err
from schema.base import Schema
from schema.brief import Brief
from schema.outline import Outline

router = APIRouter(prefix="/experiences", tags=["generation"])


class BuildRequest(Schema):
    brief: Brief
    outline: Outline
    brand_id: str | None = None


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _event_lines(event: BuildEvent) -> str:
    if isinstance(event.result, Err):
        return _sse(
            "error",
            {
                "index": event.index,
                "code": event.result.error.code,
                "message": event.result.error.message,
            },
        )
    lines = ""
    if event.repaired:
        lines += _sse("repair", {"index": event.index})
    lines += _sse(
        "scene",
        {"index": event.index, "scene": event.result.value.model_dump(by_alias=True)},
    )
    return lines


async def _events(experience_id: str, body: BuildRequest) -> AsyncIterator[str]:
    count = 0
    async for event in build_experience(
        brief=body.brief,
        approved_outline=approve_outline(body.outline),
        brand_id=body.brand_id,
        owner_id=config().local_user_id,
        experience_id=experience_id,
    ):
        yield _event_lines(event)
        if not isinstance(event.result, Err):
            count += 1
    yield _sse("done", {"count": count})


@router.post("/{experience_id}/build")
async def build(experience_id: str, body: BuildRequest) -> StreamingResponse:
    return StreamingResponse(
        _events(experience_id, body), media_type="text/event-stream"
    )
