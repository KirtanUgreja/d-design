"""Non-streaming, like Director and for the same reason: the interview
returns one thing per step — a question, or a Brief — and the client's job is
to render it, not to watch it arrive.

Stateless across steps. The client holds the answers so far and sends them
back; the server holds no interview session. That is not laziness about
persistence, it is what makes "the Brief stays visible and editable,
permanently" (docs/v1/plan/08-intake.md) the natural shape rather than a
feature bolted onto a hidden server-side conversation.
"""

from uuid import UUID

from fastapi import APIRouter

from config import config
from db.tenant import as_user
from features.intake import InterviewStep, advance, save_brief
from lib.result import Err
from routes.errors import as_http_exception
from schema.base import Schema

router = APIRouter(prefix="/experiences", tags=["intake"])


class IntakeRequest(Schema):
    # Both optional-by-default: the first call is an empty prompt box and no
    # answers, and that is a legitimate start — it comes back with the first
    # question.
    prompt: str = ""
    answers: dict[str, str] = {}  # noqa: RUF012 -- Pydantic copies field defaults per instance


@router.post("/{experience_id}/intake")
async def interview(experience_id: str, body: IntakeRequest) -> InterviewStep:
    owner_id = config().local_user_id
    result = await advance(
        prompt=body.prompt,
        answers=body.answers,
        owner_id=owner_id,
        experience_id=experience_id,
    )
    if isinstance(result, Err):
        raise as_http_exception(result.error)

    step = result.value
    # Stored the moment it exists, so the approved-claims record outlives the
    # browser tab that produced it.
    if step.brief is not None:
        async with as_user(owner_id) as session:
            await save_brief(
                session,
                owner_id=UUID(owner_id),
                experience_id=UUID(experience_id),
                brief=step.brief,
            )
    return step
