"""brand_kits FastAPI routes — thin (structure.md: "A route parses its input,
calls a feature's public function, and returns the result").

Every tenant-scoped query runs inside as_user (the one Python tenant wrapper);
RLS does the isolation. A route has no business logic beyond request shape.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from db.tenant import as_user
from features.brand_kits.auth_dependency import current_user_id
from features.brand_kits.brand_kits_data import (
    BrandKitRecord,
    create_kit,
    get_kit,
    list_kits_for_team,
    list_teams,
)
from lib.result import Err

router = APIRouter(prefix="/brand-kits", tags=["brand-kits"])

UserId = Annotated[str, Depends(current_user_id)]


class KitOut(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    id: str
    team_id: str
    name: str
    colors: dict[str, str]
    logo_ref: str | None
    font_ids: list[str]


class KitIn(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    team_id: str
    name: str = Field(min_length=1, max_length=120)
    colors: dict[str, str] = Field(default_factory=dict)
    logo_ref: str | None = None
    font_ids: list[str] = Field(default_factory=list)


def _out(k: BrandKitRecord) -> KitOut:
    return KitOut(
        id=k.id,
        team_id=k.team_id,
        name=k.name,
        colors=k.colors,
        logo_ref=k.logo_ref,
        font_ids=k.font_ids,
    )


@router.get("/teams", response_model=list[dict[str, str]])
async def list_user_teams(user_id: UserId) -> list[dict[str, str]]:
    async with as_user(user_id) as session:
        rows = await list_teams(session)
    return [{"id": t_id, "name": name} for t_id, name in rows]


@router.get("/teams/{team_id}/kits", response_model=list[KitOut])
async def list_team_kits(team_id: str, user_id: UserId) -> list[KitOut]:
    async with as_user(user_id) as session:
        kits = await list_kits_for_team(session, team_id)
    return [_out(k) for k in kits]


@router.get("/{kit_id}", response_model=KitOut)
async def kit_detail(kit_id: str, user_id: UserId) -> KitOut:
    async with as_user(user_id) as session:
        kit = await get_kit(session, kit_id)
    if kit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return _out(kit)


@router.post("", response_model=KitOut, status_code=status.HTTP_201_CREATED)
async def kit_create(body: KitIn, user_id: UserId) -> KitOut:
    async with as_user(user_id) as session:
        result = await create_kit(
            session,
            team_id=body.team_id,
            name=body.name,
            colors=body.colors,
            logo_ref=body.logo_ref,
            font_ids=body.font_ids,
        )
    # The RLS with check refused the row: the caller is not a member of the
    # team it is writing to. An expected refusal (403), not a server error.
    if isinstance(result, Err):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.error.detail)
    return _out(result.value)
