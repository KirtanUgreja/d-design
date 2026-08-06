"""The model seam, tested against a mocked transport rather than a live
OpenRouter call — the one HTTP boundary in this codebase to a paid
third-party API, where `httpx.MockTransport` (stdlib to `httpx`, no new
dependency) is the right tool instead of the real-infra-in-Docker approach
`tests/test_storage.py` and `tests/test_tenancy.py` use for Postgres and
MinIO. Quota's own atomicity and the race are tested against the real
database in `features/generation/test_quota.py`; here, quota is mocked out
so these tests isolate the seam's own logic — parse, repair, refusal.
"""

import json
from collections.abc import Callable
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import BaseModel

import ai.complete as complete_module
from ai.complete import complete
from lib.result import Err, Ok, err, ok


class _Widget(BaseModel):
    text: str


def _chunk(
    content: str | None = None,
    finish_reason: str | None = None,
    usage: dict[str, object] | None = None,
) -> str:
    choice: dict[str, object] = {"delta": {}, "finish_reason": finish_reason}
    if content is not None:
        choice["delta"] = {"content": content}
    body: dict[str, object] = {
        "model": "test/model",
        "provider": "test-provider",
        "choices": [choice],
    }
    if usage is not None:
        body["usage"] = usage
    return f"data: {json.dumps(body)}\n\n"


def _sse(*chunks: str) -> bytes:
    return ("".join(chunks) + "data: [DONE]\n\n").encode()


@pytest.fixture(autouse=True)
def _quota_always_ok(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Isolates the seam from quota/DB entirely — its atomicity and the
    race are `features/generation/test_quota.py`'s job, not this file's."""
    mock = AsyncMock(return_value=ok(None))
    monkeypatch.setattr(complete_module, "check_quota_and_kill_switch", mock)
    return mock


@pytest.fixture
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


def test_payload_asks_for_minimal_reasoning() -> None:
    """Verified live (2026-08): every model behind this seam is a reasoning
    model, and OpenRouter bills hidden reasoning tokens out of the same
    `max_tokens` budget as the visible completion — a trivial request burned
    256 reasoning tokens and returned `content: null` at the default
    setting, and `reasoning.max_tokens` did not cap it. `effort: "minimal"`
    is the lever that actually works. One structural assertion so a future
    edit cannot drop the key without a test noticing — see
    `ai/complete.py`'s `_REASONING` for the full account."""
    payload = complete_module._payload("test/model", "sys", "usr", _Widget)
    assert payload["reasoning"] == {"effort": "minimal"}


async def test_successful_completion_parses_first_try(
    monkeypatch: pytest.MonkeyPatch, _logged: AsyncMock
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        body = _sse(
            _chunk(
                json.dumps({"text": "hello"}),
                "stop",
                {"prompt_tokens": 10, "completion_tokens": 5},
            )
        )
        return httpx.Response(200, content=body)

    _install_transport(monkeypatch, handler)

    result = await complete(
        phase="build",
        schema=_Widget,
        system="sys",
        user="usr",
        owner_id="owner-1",
        experience_id="exp-1",
    )

    assert isinstance(result, Ok)
    assert result.value.value == _Widget(text="hello")
    assert result.value.repaired is False
    assert calls == 1
    _logged.assert_awaited_once()
    assert _logged.call_args.kwargs["repaired"] is False
    assert _logged.call_args.kwargs["error_class"] is None
    assert _logged.call_args.kwargs["calls"] == 1


async def test_malformed_response_triggers_exactly_one_repair(
    monkeypatch: pytest.MonkeyPatch, _logged: AsyncMock
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        content = (
            "not valid json at all" if calls == 1 else json.dumps({"text": "fixed"})
        )
        return httpx.Response(200, content=_sse(_chunk(content, "stop")))

    _install_transport(monkeypatch, handler)

    result = await complete(
        phase="build",
        schema=_Widget,
        system="sys",
        user="usr",
        owner_id="owner-1",
        experience_id="exp-1",
    )

    assert isinstance(result, Ok)
    assert result.value.value == _Widget(text="fixed")
    assert result.value.repaired is True
    assert calls == 2
    assert _logged.call_args.kwargs["repaired"] is True
    assert _logged.call_args.kwargs["calls"] == 2


async def test_repair_exhausted_after_second_failure_is_never_retried_again(
    monkeypatch: pytest.MonkeyPatch, _logged: AsyncMock
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=_sse(_chunk("still not json", "stop")))

    _install_transport(monkeypatch, handler)

    result = await complete(
        phase="build",
        schema=_Widget,
        system="sys",
        user="usr",
        owner_id="owner-1",
        experience_id="exp-1",
    )

    assert isinstance(result, Err)
    assert result.error.code == "repair_exhausted"
    assert calls == 2  # never a third attempt
    assert _logged.call_args.kwargs["error_class"] == "repair_exhausted"


async def test_refusal_via_content_filter_finish_reason(
    monkeypatch: pytest.MonkeyPatch, _logged: AsyncMock
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_sse(_chunk("", "content_filter")))

    _install_transport(monkeypatch, handler)

    result = await complete(
        phase="build",
        schema=_Widget,
        system="sys",
        user="usr",
        owner_id="owner-1",
        experience_id="exp-1",
    )

    assert isinstance(result, Err)
    assert result.error.code == "refused"
    assert _logged.call_args.kwargs["error_class"] == "refused"


async def test_refusal_via_empty_content(
    monkeypatch: pytest.MonkeyPatch, _logged: AsyncMock
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_sse(_chunk("   ", "stop")))

    _install_transport(monkeypatch, handler)

    result = await complete(
        phase="build",
        schema=_Widget,
        system="sys",
        user="usr",
        owner_id="owner-1",
        experience_id="exp-1",
    )

    assert isinstance(result, Err)
    assert result.error.code == "refused"


async def test_upstream_error_status_is_a_result_failure(
    monkeypatch: pytest.MonkeyPatch, _logged: AsyncMock
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"server error")

    _install_transport(monkeypatch, handler)

    result = await complete(
        phase="build",
        schema=_Widget,
        system="sys",
        user="usr",
        owner_id="owner-1",
        experience_id="exp-1",
    )

    assert isinstance(result, Err)
    assert result.error.code == "upstream_unavailable"


@pytest.mark.parametrize(
    ("name", "separator"),
    [
        ("line separator", "\u2028"),
        ("paragraph separator", "\u2029"),
        ("next line", "\x85"),
    ],
)
async def test_unicode_separators_in_copy_do_not_split_the_sse_payload(
    monkeypatch: pytest.MonkeyPatch, _logged: AsyncMock, name: str, separator: str
) -> None:
    """Regression, found live in CI (docs/v1/plan/06-model-seam-and-build.md).

    These three are legal *unescaped* inside a JSON string, and a JavaScript
    gateway's `JSON.stringify` does not escape them — so they reach us raw on
    the wire. `httpx.aiter_lines()` splits on all three anyway (it follows
    `str.splitlines()`), cutting one `data:` payload into two, and each half
    parses as truncated JSON: `JSONDecodeError: Unterminated string`. The
    model only has to write one of these into its copy for a whole build to
    die, so the framing has to be ours, not splitlines'.
    """
    text = f"before{separator}after"
    # `ensure_ascii=False` on BOTH dumps is the point: it puts the raw
    # character on the wire, exactly as a JS gateway's `JSON.stringify`
    # does. The default `ensure_ascii=True` escapes it to a `\\uXXXX`
    # sequence and the bug does not reproduce.
    content = json.dumps({"text": text}, ensure_ascii=False)
    body = json.dumps(
        {
            "model": "test/model",
            "provider": "test-provider",
            "choices": [{"delta": {"content": content}, "finish_reason": "stop"}],
        },
        ensure_ascii=False,
    )
    wire = f"data: {body}\n\ndata: [DONE]\n\n".encode()
    assert separator.encode() in wire, "raw separator never reached the wire"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=wire)

    _install_transport(monkeypatch, handler)

    result = await complete(
        phase="build",
        schema=_Widget,
        system="sys",
        user="usr",
        owner_id="owner-1",
        experience_id="exp-1",
    )

    assert isinstance(result, Ok), f"{name} split the payload"
    assert result.value.value.text == text


async def test_quota_exceeded_short_circuits_before_any_http_call(
    monkeypatch: pytest.MonkeyPatch,
    _quota_always_ok: AsyncMock,
    _logged: AsyncMock,
) -> None:
    _quota_always_ok.return_value = err("quota_exceeded", "halted")
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=_sse(_chunk("{}", "stop")))

    _install_transport(monkeypatch, handler)

    result = await complete(
        phase="build",
        schema=_Widget,
        system="sys",
        user="usr",
        owner_id="owner-1",
        experience_id="exp-1",
    )

    assert isinstance(result, Err)
    assert result.error.code == "quota_exceeded"
    assert calls == 0
    _logged.assert_not_awaited()
