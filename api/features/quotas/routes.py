"""quotas FastAPI routes — thin: parse, call the feature's public function
inside as_user, return. GET /entitlements is what web asks before rendering a
deck (an affordance); the authoritative spend gate is experience_create."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from db.tenant import as_user
from features.brand_kits.auth_dependency import current_user_id
from features.quotas.kill_switch import forced_plan, kill_switch_tripped
from features.quotas.quotas_data import get_entitlement

router = APIRouter(prefix="/entitlements", tags=["entitlements"])

UserId = Annotated[str, Depends(current_user_id)]


class EntitlementOut(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    plan: str
    used: int
    limit: int
    exhausted: bool
    kill_switch: bool


@router.get("", response_model=EntitlementOut)
async def entitlement(user_id: UserId) -> EntitlementOut:
    async with as_user(user_id) as session:
        e = await get_entitlement(session, user_id, forced=forced_plan())
    return EntitlementOut(
        plan=e.plan,
        used=e.used,
        limit=e.limit,
        exhausted=e.exhausted,
        kill_switch=kill_switch_tripped(),
    )
