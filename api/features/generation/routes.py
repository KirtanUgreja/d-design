"""generation FastAPI routes — thin (structure.md): parse, call the feature's
public function, return.

These are `def`, not `async def`, and that is deliberate. The seam is
synchronous httpx, and a model call takes tens of seconds; inside an `async
def` it would block the event loop for the whole time and freeze every other
request. FastAPI runs a sync route in its threadpool, which is what a blocking
call wants. The auth dependency stays async — it is awaited before the
endpoint runs.

Session-gated: every stage spends model tokens, so an anonymous caller must not
reach it. Quota-gated: no. The free tier limits hosted URLs, not generation.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from features.brand_kits.auth_dependency import current_user_id
from features.generation import build as build_stage
from features.generation import interview as interview_stage
from features.generation import mapping as mapping_stage
from features.generation import provider_configured
from features.quotas.kill_switch import kill_switch_tripped
from lib.result import Err
from schema.deck import Deck
from schema.outline import Brief, Outline

router = APIRouter(prefix="/generation", tags=["generation"])

UserId = Annotated[str, Depends(current_user_id)]


class MappingIn(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """An approved outline plus an optional explicit design family."""

    outline: Outline
    family_id: str | None = None


class BuildIn(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """A mapped deck. The images are generated here, not passed in."""

    deck: Deck


class BuildOut(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """The built deck and the image assets, keyed. The images are data URIs
    kept beside the deck because the schema has no field for them; the
    exporter inlines them at render time."""

    deck: Deck
    images: dict[str, str]


def _guard() -> None:
    """The two gates every stage shares: configured provider, and spend not
    halted. Both fail closed."""
    if not provider_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="model provider is not configured",
        )
    if kill_switch_tripped():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="service paused (kill switch)",
        )


def _upstream(detail: str) -> HTTPException:
    """A stage that failed is an upstream failure, not the caller's mistake —
    the brief was valid, the model could not deliver. 502 with the seam's own
    detail, which says which kind (refused, invalid, transport, exhausted)."""
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


@router.post("/interview", response_model=Outline)
def generation_interview(brief: Brief, user_id: UserId) -> Outline:
    """Brief -> outline. The caller shows this and gets it approved; nothing is
    mapped or built until they do. ``user_id`` is the auth gate, unused below."""
    _guard()
    result = interview_stage(brief)
    if isinstance(result, Err):
        raise _upstream(f"{result.error.kind}: {result.error.detail}")
    return result.value


@router.post("/mapping", response_model=Deck)
def generation_mapping(body: MappingIn, user_id: UserId) -> Deck:
    """An approved outline -> a per-slide Deck."""
    _guard()
    result = mapping_stage(body.outline, body.family_id)
    if isinstance(result, Err):
        raise _upstream(f"{result.error.kind}: {result.error.detail}")
    return result.value


@router.post("/build", response_model=BuildOut)
def generation_build(body: BuildIn, user_id: UserId) -> BuildOut:
    """A mapped Deck -> every slide built, plus the image assets."""
    _guard()
    result = build_stage(body.deck)
    if isinstance(result, Err):
        raise _upstream(f"{result.error.kind}: {result.error.detail}")
    built = result.value
    return BuildOut(deck=built.deck, images=built.images)
