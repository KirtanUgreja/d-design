"""generation FastAPI routes — thin (structure.md): parse, call the feature's
public function, record what it cost, return.

**The seam is a dependency.** Two reasons, and the second is the one that made
it necessary: it lets a test exercise a stage body with a stubbed seam instead
of the network, and it lets the route read `seam.stats` after the call to record
what the stage actually did (phase, model, repair, latency).

**The model call runs in a thread.** The seam is synchronous httpx and a call
takes tens of seconds, so calling it on the event loop would freeze every other
request. `asyncio.to_thread` is what a sync route was doing implicitly before;
being async here is what lets the telemetry insert be awaited.

Session-gated: every stage spends model tokens, so an anonymous caller must not
reach it. Quota-gated: no. The free tier limits hosted URLs, not generation —
the kill switch, which is a spend ceiling, does apply.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ai.complete import Seam
from ai.images import ImageSeam
from db.tenant import as_user
from features.brand_kits.auth_dependency import current_user_id
from features.generation import build as build_stage
from features.generation import interview as interview_stage
from features.generation import mapping as mapping_stage
from features.generation import new_image_seam, new_text_seam, provider_configured
from features.generation.generation import BUILD_MODEL, INTERVIEW_MODEL, MAPPING_MODEL
from features.generations import record_generation
from features.quotas.kill_switch import kill_switch_tripped
from lib.result import Err
from schema.deck import Deck
from schema.outline import Brief, Outline

router = APIRouter(prefix="/generation", tags=["generation"])

UserId = Annotated[str, Depends(current_user_id)]


def text_seam_dependency() -> Seam:
    """The text seam for this request. Overridden in tests so a stage body can
    be exercised without the network, and read by the route for its counters."""
    return new_text_seam()


def image_seam_dependency() -> ImageSeam:
    return new_image_seam()


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


async def _record(user_id: str, *, phase: str, model: str, seam: Seam, started: float) -> None:
    """Record the stage's metadata, and never fail the request doing it.

    The suppression is deliberate and narrow: this path grants nothing, and
    losing a metrics row must not cost someone the deck they just waited a
    minute for. It is the opposite of the fail-closed rule, which exists for
    paths that *grant*.
    """
    with contextlib.suppress(Exception):
        async with as_user(user_id) as session:
            await record_generation(
                session,
                phase=phase,
                model=model,
                repair=seam.stats.repairs > 0,
                latency_ms=int((time.monotonic() - started) * 1000),
            )


@router.post("/interview", response_model=Outline)
async def generation_interview(
    brief: Brief,
    user_id: UserId,
    seam: Annotated[Seam, Depends(text_seam_dependency)],
) -> Outline:
    """Brief -> outline. The caller shows this and gets it approved; nothing is
    mapped or built until they do."""
    _guard()
    started = time.monotonic()
    result = await asyncio.to_thread(interview_stage, brief, seam)
    await _record(user_id, phase="interview", model=INTERVIEW_MODEL, seam=seam, started=started)
    if isinstance(result, Err):
        raise _upstream(f"{result.error.kind}: {result.error.detail}")
    return result.value


@router.post("/mapping", response_model=Deck)
async def generation_mapping(
    body: MappingIn,
    user_id: UserId,
    seam: Annotated[Seam, Depends(text_seam_dependency)],
) -> Deck:
    """An approved outline -> a per-slide Deck."""
    _guard()
    started = time.monotonic()
    result = await asyncio.to_thread(mapping_stage, body.outline, body.family_id, seam)
    await _record(user_id, phase="mapping", model=MAPPING_MODEL, seam=seam, started=started)
    if isinstance(result, Err):
        raise _upstream(f"{result.error.kind}: {result.error.detail}")
    return result.value


@router.post("/build", response_model=BuildOut)
async def generation_build(
    body: BuildIn,
    user_id: UserId,
    seam: Annotated[Seam, Depends(text_seam_dependency)],
    images: Annotated[ImageSeam, Depends(image_seam_dependency)],
) -> BuildOut:
    """A mapped Deck -> every slide built, plus the image assets."""
    _guard()
    started = time.monotonic()
    result = await asyncio.to_thread(build_stage, body.deck, seam, images)
    await _record(user_id, phase="build", model=BUILD_MODEL, seam=seam, started=started)
    if isinstance(result, Err):
        raise _upstream(f"{result.error.kind}: {result.error.detail}")
    built = result.value
    return BuildOut(deck=built.deck, images=built.images)
