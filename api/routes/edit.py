"""Element-scoped edit. Non-streaming, like Director and Intake: there is one
thing to return — a partial, or a refusal — and the client's job is to apply
it, not to watch it arrive.

Stateless. The client sends the scene it is editing and gets back props to
merge, which it does through the same code path a property-panel edit takes
(`web/src/features/editor/patch.ts`). The server holds no editor session, so
what the user sees and what a patch applies to cannot drift apart.
"""

from uuid import UUID

from fastapi import APIRouter

from config import config
from features.edit import edit_block
from lib.result import Err
from routes.errors import as_http_exception
from schema.base import Schema
from schema.patch import EditResult
from schema.scene import Scene

router = APIRouter(prefix="/experiences", tags=["edit"])


class EditRequest(Schema):
    scene: Scene
    block_id: str
    instruction: str


# `UUID`, not `str`: the id goes on to `generations` as a uuid column, so a
# non-uuid path segment is a 422 at the edge rather than a `ValueError` raised
# from inside the seam after the model call has already been paid for. Found
# live, hitting `/edit/demo`.
@router.post("/{experience_id}/edit")
async def edit(experience_id: UUID, body: EditRequest) -> EditResult:
    result = await edit_block(
        scene=body.scene,
        block_id=body.block_id,
        instruction=body.instruction,
        owner_id=config().local_user_id,
        experience_id=str(experience_id),
    )
    if isinstance(result, Err):
        raise as_http_exception(result.error)
    return result.value
