"""Seam tests — the repair and refusal paths (python.md -> "Test").

The seam's single repair retry and its fail-visible behaviour are the load-
bearing error paths of the whole pipeline. A model that returns malformed
JSON must be repaired once, then fail visibly — never silently accepted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx

from ai.complete import MAX_REPAIR_RETRIES, Seam
from lib.result import Err, Ok
from schema.outline import Outline


@dataclass
class StubTransport:
    """A scripted transport. Each call returns the next queued response."""

    responses: list[httpx.Response]
    calls: list[dict[str, object]] = field(default_factory=list)

    def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response:
        self.calls.append({"url": url, "json": json})
        return self.responses.pop(0)


def _ok_response(payload: object, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        json={"choices": [{"message": {"content": json.dumps(payload)}}]},
    )


def _outline_payload() -> dict[str, object]:
    return {
        "title": "Launch",
        "audience": "Founders",
        "goal": "Raise",
        "sections": [
            {
                "heading": "The problem",
                "summary": "Teams waste weeks on decks",
                "claims": [
                    {"text": "Deck building is slow", "source": "user"},
                ],
            }
        ],
        "must_haves": [],
    }


def test_valid_response_returns_ok() -> None:
    transport = StubTransport([_ok_response(_outline_payload())])
    seam = Seam(transport=transport, api_key="test-key")
    result = seam.complete(phase="interview", schema=Outline, system="s", user="u", model="m")
    assert isinstance(result, Ok)
    assert result.value.title == "Launch"
    assert seam.stats.calls == 1
    assert seam.stats.repairs == 0


def test_invalid_response_is_repaired_once_then_ok() -> None:
    # First call: malformed JSON (a string, not a dict). Second call: valid.
    transport = StubTransport([_ok_response("not an outline"), _ok_response(_outline_payload())])
    seam = Seam(transport=transport, api_key="test-key")
    result = seam.complete(phase="interview", schema=Outline, system="s", user="u", model="m")
    assert isinstance(result, Ok)
    assert result.value.title == "Launch"
    assert seam.stats.calls == 2
    assert seam.stats.repairs == 1


def test_invalid_twice_fails_visibly() -> None:
    transport = StubTransport([_ok_response("bad"), _ok_response("also bad")])
    seam = Seam(transport=transport, api_key="test-key")
    result = seam.complete(phase="interview", schema=Outline, system="s", user="u", model="m")
    assert isinstance(result, Err)
    assert result.error.kind == "repair_exhausted"
    # One correction was sent; it failed. The budget is exhausted, so this
    # fails visibly rather than looping forever.
    assert seam.stats.calls == 2
    assert seam.stats.repairs == MAX_REPAIR_RETRIES


def test_transport_error_returns_transport_err() -> None:
    transport = StubTransport([httpx.Response(500, json={"error": "boom"})])
    seam = Seam(transport=transport, api_key="test-key")
    result = seam.complete(phase="interview", schema=Outline, system="s", user="u", model="m")
    assert isinstance(result, Err)
    assert result.error.kind == "transport"


def test_missing_api_key_fails_closed() -> None:
    seam = Seam(transport=StubTransport([]), api_key="")
    result = seam.complete(phase="interview", schema=Outline, system="s", user="u", model="m")
    assert isinstance(result, Err)
    assert result.error.kind == "transport"
    assert seam.stats.calls == 0


def test_repair_resends_with_correction_context() -> None:
    transport = StubTransport([_ok_response("bad"), _ok_response(_outline_payload())])
    seam = Seam(transport=transport, api_key="test-key")
    seam.complete(phase="interview", schema=Outline, system="s", user="u", model="m")
    # The second call's messages must include the correction frame.
    second = transport.calls[1]["json"]
    assert isinstance(second, dict)
    messages = second["messages"]
    assert isinstance(messages, list)
    last = messages[-1]
    assert isinstance(last, dict)
    assert last["role"] == "user"
    assert "did not match the required schema" in last["content"]
