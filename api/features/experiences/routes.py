"""experiences FastAPI routes — thin (structure.md): parse, call the feature's
public function inside as_user, return. RLS does the isolation.

**Saving is free; publishing spends.** The routes are split along that line:
`POST` and `PUT` write a draft, `POST /{id}/publish` sets the hosted key and is
the only place the quota is consumed. Charging a save would spend a free
account's single hosted URL before it had published anything — and the tier
says "1 hosted URL", not "1 saved deck".
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from db.tenant import as_user
from features.brand_kits.auth_dependency import current_user_id
from features.experiences.experiences_data import (
    ExperienceRecord,
    get_experience,
    list_experiences,
    save_experience,
    set_published_key,
    update_experience,
)
from features.quotas.kill_switch import effective_plan, kill_switch_tripped
from features.quotas.quotas_data import consume_quota, plan_limit
from lib.result import Err

router = APIRouter(prefix="/experiences", tags=["experiences"])

UserId = Annotated[str, Depends(current_user_id)]


class ExperienceOut(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    id: str
    title: str
    deck_json: str
    images_json: str
    published_key: str | None


class ExperienceIn(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    title: str = Field(min_length=1, max_length=120)
    deck_json: str = Field(min_length=1)
    # The image sidecar: a JSON object of data URIs keyed by slide id. Defaulted
    # because most decks have no images to carry.
    images_json: str = Field(default="{}")


class PublishIn(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    published_key: str = Field(min_length=1, max_length=200)


def _out(e: ExperienceRecord) -> ExperienceOut:
    return ExperienceOut(
        id=e.id,
        title=e.title,
        deck_json=e.deck_json,
        images_json=e.images_json,
        published_key=e.published_key,
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")


@router.get("", response_model=list[ExperienceOut])
async def list_user_experiences(user_id: UserId) -> list[ExperienceOut]:
    async with as_user(user_id) as session:
        rows = await list_experiences(session)
    return [_out(r) for r in rows]


@router.get("/{experience_id}", response_model=ExperienceOut)
async def experience_detail(experience_id: str, user_id: UserId) -> ExperienceOut:
    async with as_user(user_id) as session:
        exp = await get_experience(session, experience_id)
    if exp is None:
        raise _not_found()
    return _out(exp)


@router.post("", response_model=ExperienceOut, status_code=status.HTTP_201_CREATED)
async def experience_create(body: ExperienceIn, user_id: UserId) -> ExperienceOut:
    """Create a draft. No quota: a save is not a hosted URL."""
    async with as_user(user_id) as session:
        exp = await save_experience(
            session,
            title=body.title,
            deck_json=body.deck_json,
            images_json=body.images_json,
        )
    # The RLS with check refused the row: the caller is not the owner the policy
    # requires. An expected refusal (403), not a server error.
    if isinstance(exp, Err):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exp.error.detail)
    return _out(exp.value)


@router.put("/{experience_id}", response_model=ExperienceOut)
async def experience_update(
    experience_id: str, body: ExperienceIn, user_id: UserId
) -> ExperienceOut:
    """Update a draft in place. No quota — an edit is not a new hosted URL."""
    async with as_user(user_id) as session:
        exp = await update_experience(
            session,
            experience_id,
            title=body.title,
            deck_json=body.deck_json,
            images_json=body.images_json,
        )
    if isinstance(exp, Err):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exp.error.detail)
    if exp.value is None:
        # No row matched: the policy excluded it, or it does not exist. The two
        # are indistinguishable on purpose — a 404 must not confirm that
        # another tenant's row is there.
        raise _not_found()
    return _out(exp.value)


@router.post("/{experience_id}/publish", response_model=ExperienceOut)
async def experience_publish(experience_id: str, body: PublishIn, user_id: UserId) -> ExperienceOut:
    """Record the hosted artefact and spend a hosted URL.

    The authoritative, transactional spend gate (phase 19). The quota is
    consumed in the SAME transaction as the update — a refused check rolls the
    write back too. Fail-closed: a kill switch or a quota that cannot run
    refuses (AGENTS.md rule 10). The artefact has already been rendered and
    stored by web, which removes it if this refuses.
    """
    plan = effective_plan()
    limit = plan_limit(plan)
    async with as_user(user_id) as session:
        if kill_switch_tripped():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="service paused (kill switch)",
            )
        refused = await consume_quota(session, user_id, plan=plan, limit=limit)
        if refused is not None:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"free tier includes {refused.limit} hosted URL"
                + ("" if refused.limit == 1 else "s"),
            )
        exp = await set_published_key(session, experience_id, published_key=body.published_key)
    if isinstance(exp, Err):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exp.error.detail)
    if exp.value is None:
        raise _not_found()
    return _out(exp.value)
