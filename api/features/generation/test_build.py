"""`build_experience`'s own approval boundary
(docs/v1/plan/07-director.md -> "The gate is the product decision"): it
takes `ApprovedOutline`, not `Outline`, and that is not only a static
mypy fact. Mocked transport, same pattern as `ai/test_complete.py`.
"""

import json
from collections.abc import Callable
from unittest.mock import AsyncMock

import httpx
import pytest

import ai.complete as complete_module
from features.director import approve_outline
from features.generation.build import BuildEvent, build_experience
from lib.result import Err, Ok, ok
from schema.brief import Brief, BriefCta
from schema.outline import Outline
from schema.scene import HeadlineProps

_BRIEF = Brief(
    goal="Launch a thing",
    audience="People who might buy it",
    key_messages=["It is fast", "It is cheap", "It is reliable"],
    proof_points=[],
    tone="confident",
    cta=BriefCta(label="Get started", href="https://example.com"),
)

# A real uuid: `build_experience` opens an `as_user` session to read the brand
# kit and the asset list, so the owner id reaches Postgres rather than only the
# mocked seam.
_OWNER = "00000000-0000-4000-8000-00000000000a"

_OUTLINE = Outline.model_validate(
    {
        "title": "A narrative",
        "scenes": [
            {"intent": "hook", "beat": "open strong", "layoutHint": "centered"},
            {"intent": "problem", "beat": "name the pain", "layoutHint": "split-left"},
            {"intent": "cta", "beat": "ask for the click", "layoutHint": "centered"},
        ],
    }
)


@pytest.fixture(autouse=True)
def _quota_always_ok(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value=ok(None))
    monkeypatch.setattr(complete_module, "check_quota_and_kill_switch", mock)
    return mock


@pytest.fixture(autouse=True)
def _logged(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(complete_module, "log_generation", mock)
    return mock


def _install_transport(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    real_client = httpx.AsyncClient

    def _client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "AsyncClient", _client)


async def test_build_experience_runs_against_an_approved_outline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        scene = {
            "id": "s1",
            "intent": "hook",
            "layout": "centered",
            "blocks": [{"id": "b1", "props": {"type": "headline", "text": "Hi"}}],
        }
        body = {
            "model": "test/model",
            "provider": "test-provider",
            "choices": [
                {
                    "delta": {"content": json.dumps(scene)},
                    "finish_reason": "stop",
                }
            ],
        }
        return httpx.Response(
            200, content=f"data: {json.dumps(body)}\n\ndata: [DONE]\n\n".encode()
        )

    _install_transport(monkeypatch, handler)

    events = [
        event
        async for event in build_experience(
            brief=_BRIEF,
            approved_outline=approve_outline(_OUTLINE),
            brand_id=None,
            owner_id=_OWNER,
            experience_id="exp-1",
        )
    ]

    assert len(events) == 3
    assert all(isinstance(e.result, Ok) for e in events)


async def test_a_bare_outline_is_rejected_at_runtime_not_only_by_mypy() -> None:
    """The static boundary (`ApprovedOutline` in the signature) has a real
    runtime consequence too: `build_experience` reads
    `approved_outline.outline`, and a bare `Outline` has no such attribute.
    Bypassing `approve_outline` fails loudly instead of silently building
    against an outline nobody approved. Reaching this at all already
    requires a `# type: ignore` at the call site — an honest mistake stops
    at mypy; this is the backstop for someone overriding that on purpose.
    """
    generator = build_experience(
        brief=_BRIEF,
        approved_outline=_OUTLINE,  # type: ignore[arg-type]
        brand_id=None,
        owner_id=_OWNER,
        experience_id="exp-1",
    )
    with pytest.raises(AttributeError):
        await anext(generator)


def _responder(
    texts: list[str],
) -> tuple[Callable[[httpx.Request], httpx.Response], list[int]]:
    """A transport that returns each headline in `texts` in turn, repeating the
    last one once exhausted, and counts the calls it served."""
    calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        text = texts[min(calls[0], len(texts) - 1)]
        calls[0] += 1
        scene = {
            "id": "s1",
            "intent": "hook",
            "layout": "centered",
            "blocks": [{"id": "b1", "props": {"type": "headline", "text": text}}],
        }
        body = {
            "model": "test/model",
            "provider": "test-provider",
            "choices": [
                {"delta": {"content": json.dumps(scene)}, "finish_reason": "stop"}
            ],
        }
        return httpx.Response(
            200, content=f"data: {json.dumps(body)}\n\ndata: [DONE]\n\n".encode()
        )

    return handler, calls


async def _build_all(
    monkeypatch: pytest.MonkeyPatch, texts: list[str]
) -> tuple[list[BuildEvent], int]:
    handler, calls = _responder(texts)
    _install_transport(monkeypatch, handler)
    events = [
        event
        async for event in build_experience(
            brief=_BRIEF,
            approved_outline=approve_outline(_OUTLINE),
            brand_id=None,
            owner_id=_OWNER,
            experience_id="exp-1",
        )
    ]
    return events, calls[0]


async def test_truncated_copy_is_drawn_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """The seam's own repair cannot see this: the provider cuts copy at
    `maxLength` during decoding, so what arrives parses cleanly and there is no
    ValidationError to build a repair prompt from
    (docs/v1/plan/06-model-seam-and-build.md -> "Open defect"). Asking again is
    the remedy, and a second draw is a genuinely different roll."""
    events, calls = await _build_all(
        monkeypatch, ["A headline cut off mid-\n", "A headline that is whole"]
    )
    event = events[0]
    # Scene 0 costs two calls (truncated, then redrawn); scenes 1 and 2 cost
    # one each, since the responder repeats its last, clean text.
    assert calls == 4
    assert isinstance(event.result, Ok)
    props = event.result.value.blocks[0].props
    assert isinstance(props, HeadlineProps)
    assert props.text == "A headline that is whole"
    # Surfaces as a repair, which the client renders as nothing at all —
    # showing a user a self-correction is honesty nobody asked for
    # (docs/design/app.md -> "3. The generation watch").
    assert event.repaired is True


async def test_copy_still_truncated_after_the_retry_is_dropped_not_shipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Losing the scene beats publishing garbled copy. "Failure at scene 6 of 8
    keeps the five" is already how this loop degrades."""
    events, calls = await _build_all(monkeypatch, ["Still cut off mid-\n"])
    # Two calls per scene: the draw and the one retry. Never more — an
    # unbounded redraw on a model that truncates every time is a
    # denial-of-wallet, which is the same reason repair is capped at one.
    assert calls == 6
    assert all(isinstance(e.result, Err) for e in events)
    first = events[0].result
    assert isinstance(first, Err)
    assert "truncated" in first.error.message


async def test_clean_copy_costs_exactly_one_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The check must not add a model call to the normal path."""
    events, calls = await _build_all(monkeypatch, ["A perfectly ordinary headline"])
    assert calls == 3
    assert all(isinstance(e.result, Ok) for e in events)
    assert all(e.repaired is False for e in events)
