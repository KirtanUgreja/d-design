"""Seam tests — the repair, truncation and cost paths.

These are the load-bearing error paths of the whole engine, and each test
below is a regression for a bug v3's seam actually had.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel

from engine import ModelError, Seam, parse_fenced
from engine.llm.openrouter import MAX_REPAIRS, Reply, strict_schema
from lib.result import Err, Ok, Result


class Thing(BaseModel):
    name: str
    count: int


@dataclass
class StubTransport:
    """A scripted transport. Each call returns the next queued response."""

    responses: list[httpx.Response]
    bodies: list[dict[str, object]] = field(default_factory=list)

    async def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response:
        assert isinstance(json, dict)
        # Snapshot: the seam appends to `messages` after a failed parse.
        self.bodies.append({**json, "messages": list(json["messages"])})
        return self.responses.pop(0)


async def _no_sleep(_: float) -> None:
    return None


def _reply(
    content: str, *, finish: str = "stop", cost: float = 0.01, status: int = 200
) -> httpx.Response:
    return httpx.Response(
        status,
        json={
            "choices": [{"message": {"content": content}, "finish_reason": finish}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "cost": cost,
                "prompt_tokens_details": {"cached_tokens": 80},
            },
        },
    )


def _seam(*responses: httpx.Response) -> tuple[Seam, StubTransport]:
    transport = StubTransport(list(responses))
    return Seam(api_key="k", transport=transport, sleep=_no_sleep), transport


def _json(seam: Seam) -> Result[Thing, ModelError]:
    return asyncio.run(seam.complete_json("smoke", Thing, system="s", user="u", model="m"))


def test_valid_answer_is_ok_and_costed() -> None:
    seam, _ = _seam(_reply(json.dumps({"name": "a", "count": 2})))
    result = _json(seam)
    assert isinstance(result, Ok) and result.value.count == 2
    assert len(seam.ledger) == 1
    assert seam.ledger[0].cost_usd == 0.01
    assert seam.ledger[0].cached_tokens == 80
    assert seam.spent_usd == 0.01


def test_not_json_at_all_is_repaired_not_crashed() -> None:
    # v3: `raw` was unbound here and the repair path raised UnboundLocalError.
    seam, transport = _seam(
        _reply("Sure! Here is the thing you asked for."),
        _reply(json.dumps({"name": "a", "count": 1})),
    )
    assert isinstance(_json(seam), Ok)
    assert len(transport.bodies) == 2


def test_repair_carries_the_real_previous_answer() -> None:
    # v3 sent "" as the model's previous answer when it was valid JSON of the
    # wrong shape, so the model could not see what it had written.
    bad = json.dumps({"name": "a"})
    seam, transport = _seam(_reply(bad), _reply(json.dumps({"name": "a", "count": 1})))
    assert isinstance(_json(seam), Ok)
    messages = transport.bodies[1]["messages"]
    assert isinstance(messages, list)
    assert messages[2] == {"role": "assistant", "content": bad}
    assert "count" in str(messages[3])


def test_repair_is_per_call_not_per_seam() -> None:
    # v3 counted repairs on the seam, so a deck got one repair in total.
    good = json.dumps({"name": "a", "count": 1})
    seam, _ = _seam(_reply("nope"), _reply(good), _reply("nope"), _reply(good))
    assert isinstance(_json(seam), Ok)
    assert isinstance(_json(seam), Ok)


def test_repair_is_bounded() -> None:
    seam, transport = _seam(*[_reply("nope") for _ in range(MAX_REPAIRS + 1)])
    result = _json(seam)
    assert isinstance(result, Err) and result.error.kind == "repair_exhausted"
    assert len(transport.bodies) == MAX_REPAIRS + 1


def test_truncated_answer_is_a_failure_never_parsed() -> None:
    # A cut-off answer that happens to validate is the worst outcome.
    seam, _ = _seam(_reply(json.dumps({"name": "a", "count": 1}), finish="length"))
    result = _json(seam)
    assert isinstance(result, Err) and result.error.kind == "truncated"
    assert seam.ledger[0].ok is False
    assert seam.ledger[0].cost_usd == 0.01  # it was still paid for


def test_429_backs_off_then_succeeds() -> None:
    seam, transport = _seam(
        httpx.Response(429, json={}), _reply(json.dumps({"name": "a", "count": 1}))
    )
    assert isinstance(_json(seam), Ok)
    assert len(transport.bodies) == 2
    assert len(seam.ledger) == 1


def test_persistent_5xx_is_a_transport_error() -> None:
    seam, _ = _seam(*[httpx.Response(503, json={}) for _ in range(3)])
    result = _json(seam)
    assert isinstance(result, Err) and result.error.kind == "transport"


def test_no_key_never_calls() -> None:
    transport = StubTransport([])
    seam = Seam(api_key="", transport=transport)
    result = _json(seam)
    assert isinstance(result, Err) and result.error.kind == "no_key"
    assert transport.bodies == []


def test_text_mode_parses_fenced_blocks_and_repairs() -> None:
    def parse(reply: Reply) -> Result[dict[str, str], str]:
        return parse_fenced(reply.text, "html", "css")

    good = '```html\n<section class="s"></section>\n```\n```css\n.s{}\n```'
    seam, _ = _seam(_reply("```html\n<p></p>\n```"), _reply(good))
    result = asyncio.run(seam.complete_text("compose", parse, system="s", user="u", model="m"))
    assert isinstance(result, Ok)
    assert result.value["css"] == ".s{}"


def test_prefix_is_sent_as_a_cacheable_block() -> None:
    seam, transport = _seam(_reply(json.dumps({"name": "a", "count": 1})))
    asyncio.run(seam.complete_json("smoke", Thing, system="s", user="u", model="m", prefix="RULES"))
    system = transport.bodies[0]["messages"]
    assert isinstance(system, list)
    first = system[0]["content"][0]
    assert first["text"] == "RULES" and first["cache_control"] == {"type": "ephemeral"}


def test_citations_are_returned() -> None:
    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": "x",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url_citation": {
                                    "url": "https://a.b",
                                    "title": "T",
                                    "content": "C",
                                },
                            }
                        ],
                    },
                    "finish_reason": "stop",
                }
            ]
        },
    )
    seam, _ = _seam(response)

    def parse(reply: Reply) -> Result[Reply, str]:
        return Ok(reply)

    result = asyncio.run(seam.complete_text("research", parse, system="s", user="u", model="m"))
    assert isinstance(result, Ok)
    assert result.value.citations[0].url == "https://a.b"


def test_strict_schema_requires_everything_and_closes_objects() -> None:
    strict = strict_schema(Thing.model_json_schema())
    assert isinstance(strict, dict)
    assert strict["additionalProperties"] is False
    assert strict["required"] == ["count", "name"]


def test_a_budget_check_that_throws_refuses_the_call() -> None:
    transport = StubTransport([_reply('{"name": "a", "count": 1}')])

    def broken() -> bool:
        raise RuntimeError("the ledger is unreadable")

    seam = Seam(api_key="k", transport=transport, sleep=_no_sleep, allow=broken)
    result = asyncio.run(seam.complete_json("smoke", Thing, system="s", user="u", model="m"))
    assert isinstance(result, Err) and result.error.kind == "budget"
    assert transport.bodies == []  # nothing was sent


def test_a_spent_budget_refuses_the_repair_too() -> None:
    transport = StubTransport([_reply("not json", cost=0.5), _reply('{"name": "a", "count": 1}')])
    seam = Seam(api_key="k", transport=transport, sleep=_no_sleep)
    seam.allow = lambda: seam.spent_usd < 0.4
    result = asyncio.run(seam.complete_json("smoke", Thing, system="s", user="u", model="m"))
    assert isinstance(result, Err) and result.error.kind == "budget"
    assert len(transport.bodies) == 1  # the first call went out; the repair did not
