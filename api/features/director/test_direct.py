"""Brief -> Outline through the real seam, mocked transport — the same
`httpx.MockTransport` approach `ai/test_complete.py` uses, for the same
reason: this is the one HTTP boundary to a paid third-party API. Quota is
mocked out here too, isolating Director's own logic (the prompt, the
post-call `check_outline`) from quota's DB mechanics, which has its own
tests in `features/generation/test_quota.py`.
"""

import json
from collections.abc import Callable
from unittest.mock import AsyncMock

import httpx
import pytest

import ai.complete as complete_module
from features.director.direct import direct_brief
from lib.result import Err, Ok, ok
from schema.brief import Brief, BriefCta

_BRIEF = Brief(
    goal="Launch a thing",
    audience="People who might buy it",
    key_messages=["It is fast", "It is cheap", "It is reliable"],
    proof_points=[],
    tone="confident",
    cta=BriefCta(label="Get started", href="https://example.com"),
)

_VALID_OUTLINE = {
    "title": "A narrative",
    "scenes": [
        {"intent": "hook", "beat": "open strong", "layoutHint": "centered"},
        {"intent": "problem", "beat": "name the pain", "layoutHint": "split-left"},
        {"intent": "cta", "beat": "ask for the click", "layoutHint": "centered"},
    ],
}


def _chunk(content: str, finish_reason: str = "stop") -> str:
    body = {
        "model": "test/model",
        "provider": "test-provider",
        "choices": [{"delta": {"content": content}, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(body)}\n\n"


def _sse(*chunks: str) -> bytes:
    return ("".join(chunks) + "data: [DONE]\n\n").encode()


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


async def test_brief_becomes_a_valid_outline(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_sse(_chunk(json.dumps(_VALID_OUTLINE))))

    _install_transport(monkeypatch, handler)

    result = await direct_brief(brief=_BRIEF, owner_id="owner-1", experience_id="exp-1")

    assert isinstance(result, Ok)
    assert result.value.title == "A narrative"
    assert [s.intent for s in result.value.scenes] == ["hook", "problem", "cta"]


async def test_missing_layout_hint_fails_check_outline_not_the_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model can write a perfectly schema-valid Outline that still
    fails `check_outline` — a scene with no layoutHint parses fine (the
    field is optional) and is exactly what this check exists to catch."""
    incomplete = json.loads(json.dumps(_VALID_OUTLINE))
    incomplete["scenes"][1]["layoutHint"] = None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_sse(_chunk(json.dumps(incomplete))))

    _install_transport(monkeypatch, handler)

    result = await direct_brief(brief=_BRIEF, owner_id="owner-1", experience_id="exp-1")

    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"


async def test_malformed_response_still_gets_the_seams_one_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Director "gets no retry of its own" (docs/v1/plan/07-director.md) —
    but it still gets the seam's one repair, the same as every other
    phase. This proves Director didn't accidentally opt out of it."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        content = "not json" if calls == 1 else json.dumps(_VALID_OUTLINE)
        return httpx.Response(200, content=_sse(_chunk(content)))

    _install_transport(monkeypatch, handler)

    result = await direct_brief(brief=_BRIEF, owner_id="owner-1", experience_id="exp-1")

    assert isinstance(result, Ok)
    assert calls == 2
