"""experiences FastAPI routes — thin (structure.md): parse, call the feature's
public function inside as_user, return. RLS does the isolation."""

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
)
from features.quotas.kill_switch import effective_plan, kill_switch_tripped
from features.quotas.quotas_data import consume_quota, plan_limit

router = APIRouter(prefix="/experiences", tags=["experiences"])

UserId = Annotated[str, Depends(current_user_id)]


class ExperienceOut(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    id: str
    title: str
    deck_json: str
    published_key: str | None


class ExperienceIn(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    title: str = Field(min_length=1, max_length=120)
    deck_json: str = Field(min_length=1)
    published_key: str | None = None


def _out(e: ExperienceRecord) -> ExperienceOut:
    return ExperienceOut(
        id=e.id, title=e.title, deck_json=e.deck_json, published_key=e.published_key
    )


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return _out(exp)


@router.post("", response_model=ExperienceOut, status_code=status.HTTP_201_CREATED)
async def experience_create(body: ExperienceIn, user_id: UserId) -> ExperienceOut:
    # The authoritative, transactional spend gate (phase 19). The quota is
    # consumed in the SAME transaction as the experiences insert — a refused
    # check rolls the insert back too. Fail-closed: a kill switch or a quota
    # that cannot run refuses (AGENTS.md rule 10).
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
        exp = await save_experience(
            session,
            title=body.title,
            deck_json=body.deck_json,
            published_key=body.published_key,
        )
    return _out(exp)
