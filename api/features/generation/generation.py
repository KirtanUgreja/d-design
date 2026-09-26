"""Generation — the v1 pipeline, reachable over HTTP (v3).

The pipeline itself is unchanged: ``run_interview`` → ``run_mapping`` →
``run_build``, each returning a ``Result``. What is new is only the wiring.
Until now the only way in was ``cli.py``, so the product's front half —
"type a topic, get a deck" — existed solely in a terminal.

Three stages rather than one call, because the human gate sits between the
first two: the outline is shown and approved before anything is mapped or
built (v1 spec, the trust device — an invented claim is visible before a slide
is). The client holds the outline between calls, which is why these functions
are stateless: no session, no draft row, nothing to clean up.

The seams are per request; the sockets are not. ``ImageSeam`` counts the
images it has made against a per-deck cap, so a shared seam would count across
decks and start refusing once the first deck used its four. An ``httpx.Client``
per request would instead leak connections, so the client is shared and only
the seam is fresh — the same split as ``db/session.py``'s one engine.
"""

from __future__ import annotations

import os

import httpx

from ai.complete import ModelError, Seam, make_seam
from ai.images import ImageSeam, make_image_seam
from lib.result import Result
from pipeline.interview.interview import run_interview
from pipeline.mapping.mapping import run_mapping
from pipeline.slide_builder.slide_builder import BuildResult, run_build
from schema.deck import Deck
from schema.outline import Brief, Outline

# Per-stage models, because the stages are not equally hard. Measured on one
# fixed brief and outline, four mapping samples per model (docs/findings.md):
#
#   mapping, openai/gpt-4o-mini         0/3   the mini tier cannot hold the
#                                             deck's cross-field constraints
#   mapping, openai/gpt-4o              3/4   fast, but one layout-grammar slip
#   mapping, anthropic/claude-sonnet-4.5 4/4  and 6-8 distinct layouts of 7-8
#
# Mapping is the stage that must satisfy the whole deck at once — every region
# filled, every span legal in the family's grammar, layouts distributed. It is
# also the stage whose output is the product's claim, so its variety matters
# as much as its validity: sonnet produced near-all-distinct layouts where
# gpt-4o repeated one.
#
# Interview and build keep a cheaper default, which is what the CLI uses and
# what the live end-to-end run built six slides with. Env-overridable because
# changing an eval parameter should not need a code edit.
INTERVIEW_MODEL = os.environ.get("DDESIGN_INTERVIEW_MODEL", "openai/gpt-4o-mini")
MAPPING_MODEL = os.environ.get("DDESIGN_MAPPING_MODEL", "anthropic/claude-sonnet-4.5")
BUILD_MODEL = os.environ.get("DDESIGN_BUILD_MODEL", "openai/gpt-4o-mini")
IMAGE_MODEL = os.environ.get("DDESIGN_IMAGE_MODEL", "openai/gpt-5-image-mini")

_text_client: httpx.Client | None = None
_image_client: httpx.Client | None = None


def provider_configured() -> bool:
    """Whether the model provider has credentials.

    Fail closed (AGENTS.md rule 10): without a key the stages refuse up front
    rather than reaching the seam and coming back as an upstream failure.
    """
    return bool(os.environ.get("OPENROUTER_API_KEY", ""))


def new_text_seam() -> Seam:
    """A text seam for one request, over the shared client."""
    global _text_client
    if _text_client is None:
        _text_client = httpx.Client(timeout=120.0)
    return make_seam(_text_client)


def new_image_seam() -> ImageSeam:
    """An image seam for one request, over the shared client. Fresh per request
    so the per-deck image cap counts one deck (see the module doc). Named `new_`
    so it cannot be shadowed by the `image_seam` parameter below."""
    global _image_client
    if _image_client is None:
        _image_client = httpx.Client(timeout=180.0)
    return make_image_seam(_image_client)


def interview(brief: Brief, seam: Seam | None = None) -> Result[Outline, ModelError]:
    """Stage one: the brief becomes a schema-validated outline for approval."""
    return run_interview(
        brief, seam if seam is not None else new_text_seam(), model=INTERVIEW_MODEL
    )


def mapping(
    outline: Outline,
    family_id: str | None = None,
    seam: Seam | None = None,
) -> Result[Deck, ModelError]:
    """Stage two: an approved outline becomes a per-slide Deck."""
    return run_mapping(
        outline,
        seam if seam is not None else new_text_seam(),
        model=MAPPING_MODEL,
        family_id=family_id,
    )


def build(
    deck: Deck,
    seam: Seam | None = None,
    image_seam: ImageSeam | None = None,
) -> Result[BuildResult, ModelError]:
    """Stage three: every slide built, one call each, images where the deck asks."""
    return run_build(
        deck,
        seam if seam is not None else new_text_seam(),
        image_seam if image_seam is not None else new_image_seam(),
        model=BUILD_MODEL,
        image_model=IMAGE_MODEL,
    )
