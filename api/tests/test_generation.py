"""Generation tests — the pipeline reached through the HTTP surface.

The routes are thin, so what is worth asserting is the wiring the product
depended on and did not have: the stages exist behind a session, the provider
gate fails closed, and the seams are the ones the feature passes (never the
network). The seam's own repair/refusal paths are test_seam.py's subject.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ai.complete import ModelError, Phase, Seam, T
from ai.images import ImageError, ImageSeam
from app import app
from features.brand_kits.auth_dependency import current_user_id
from features.generation import (
    IMAGE_MODEL,
    INTERVIEW_MODEL,
    MAPPING_MODEL,
    build,
    interview,
    mapping,
)
from lib.result import Ok, Result, err, ok
from schema.outline import Brief, Outline
from tests.fixtures import golden_deck

BRIEF = {
    "topic": "Launching a new CRM for agencies",
    "slide_count": 6,
    "audience": "Agency founders",
    "goal": "Get 20 pilot signups",
}

# Any UUID: the dependency is overridden in the HTTP tests, so this only has to
# be a value the auth layer would have produced.
USER_ID = "00000000-0000-0000-0000-0000000000aa"


class FakeSeam(Seam):
    """A seam that returns a scripted result and records the model asked for."""

    def __init__(self, result: Result[object, ModelError]) -> None:
        self._result = result
        self.captured_model = ""

    def complete(
        self,
        phase: Phase,
        schema: type[T],
        system: str,
        user: str,
        model: str,
        route: str = "openrouter/auto",
        image: str | None = None,
    ) -> Result[T, ModelError]:
        del phase, schema, system, user, route, image
        self.captured_model = model
        return self._result  # type: ignore[return-value]  # the scripted schema


class FakeImageSeam(ImageSeam):
    """An image seam that returns a fixed data URI and counts its calls."""

    def __init__(self) -> None:
        self.generated: list[str] = []

    def generate(
        self,
        subject: str,
        visual_rules: str,
        model: str = IMAGE_MODEL,
    ) -> Result[str, ImageError]:
        del visual_rules, model
        self.generated.append(subject)
        return ok("data:image/png;base64,AAAA")


def _brief() -> Brief:
    return Brief.model_validate(BRIEF)


def _outline() -> Outline:
    return Outline.model_validate(
        {
            "title": "The agency CRM",
            "audience": "Agency founders",
            "goal": "Get 20 pilot signups",
            "sections": [
                {
                    "heading": "The problem",
                    "summary": "Agencies track clients in spreadsheets and lose margin.",
                    "claims": [
                        {"text": "Agencies lose hours a week to tracking", "source": "user"}
                    ],
                }
            ],
        }
    )


# --- the seam is the injected one, and it is the shared model ---------------


def test_interview_uses_the_injected_seam_and_the_shared_model() -> None:
    seam = FakeSeam(ok(_outline()))

    result = interview(_brief(), seam)

    assert isinstance(result, Ok)
    assert result.value.title == "The agency CRM"
    assert seam.captured_model == INTERVIEW_MODEL


def test_mapping_uses_its_own_measured_model() -> None:
    """Mapping is the reliability bottleneck and the variety claim, so it runs
    a different model from the cheaper stages (docs/findings.md)."""
    seam = FakeSeam(ok(golden_deck()))

    result = mapping(_outline(), seam=seam)

    assert isinstance(result, Ok)
    assert result.value.family_id == "editorial-serif"
    assert seam.captured_model == MAPPING_MODEL
    assert MAPPING_MODEL != INTERVIEW_MODEL


def test_build_passes_both_seams_and_keys_images_by_slide() -> None:
    """Build calls the text seam once per slide, and the image seam once per
    image block, keyed by the *mapped* slide id — the key the renderer's
    `images` map expects."""
    deck = golden_deck()
    with_image = next(
        slide for slide in deck.slides if any(block.kind == "image" for block in slide.blocks)
    )
    image_seam = FakeImageSeam()

    result = build(deck, FakeSeam(ok(with_image)), image_seam)

    assert isinstance(result, Ok)
    assert len(result.value.deck.slides) == len(deck.slides)
    assert set(result.value.images) == {slide.id for slide in deck.slides}
    assert len(image_seam.generated) == len(deck.slides)


def test_a_stage_failure_is_a_result_not_an_exception() -> None:
    seam = FakeSeam(err(ModelError("transport", "model endpoint returned 500")))

    result = interview(_brief(), seam)

    assert not isinstance(result, Ok)
    assert result.error.kind == "transport"


# --- the HTTP surface -------------------------------------------------------


def test_the_stage_exists_and_is_session_gated() -> None:
    """No Authorization header: the auth dependency refuses before any work."""
    response = TestClient(app).post("/generation/interview", json=BRIEF)

    assert response.status_code == 401


def test_an_unconfigured_provider_refuses_instead_of_calling_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed (AGENTS.md rule 10). With a session but no key the stage
    answers 503 — it must not reach the seam and return a 502 upstream."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    app.dependency_overrides[current_user_id] = lambda: USER_ID
    try:
        response = TestClient(app).post("/generation/interview", json=BRIEF)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "model provider is not configured"


def test_the_kill_switch_halts_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Denial of wallet: the global spend ceiling stops model spend, not only
    publishing."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("KILL_SWITCH", "1")
    app.dependency_overrides[current_user_id] = lambda: USER_ID
    try:
        response = TestClient(app).post("/generation/interview", json=BRIEF)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "service paused (kill switch)"
