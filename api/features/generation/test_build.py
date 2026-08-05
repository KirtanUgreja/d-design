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
from features.generation.build import build_experience
from lib.result import Ok, ok
from schema.brief import Brief, BriefCta
from schema.outline import Outline

_BRIEF = Brief(
    goal="Launch a thing",
    audience="People who might buy it",
    key_messages=["It is fast", "It is cheap", "It is reliable"],
    proof_points=[],
    tone="confident",
    cta=BriefCta(label="Get started", href="https://example.com"),
)

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
            owner_id="owner-1",
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
        owner_id="owner-1",
        experience_id="exp-1",
    )
    with pytest.raises(AttributeError):
        await anext(generator)
