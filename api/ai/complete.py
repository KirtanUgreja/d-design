"""The one call site for model access in the codebase (docs/coderules/patterns.md
rule 6). Plain `httpx` against OpenRouter's OpenAI-compatible endpoint — not
Instructor, not an agent framework (docs/techstack/ai-stack.md). The pipeline
is four sequential calls the caller decides between, with a human gate in the
middle; a framework would express that as a graph, add a state model and a
debugging surface, and buy nothing.

Owns six things a second call path would drop
(docs/v1/plan/06-model-seam-and-build.md):

  1. The Pydantic parse of the response — the real gate, decoder or not
  2. One repair retry — the scene, the specific errors, nothing else
  3. Refusal normalization — a decline can arrive as a *successful* response
  4. The metadata log — model id and route, tokens and calls, never content
  5. Tool-call caps — n/a in v1: Build's tier-0 reads are plain function
     calls in features/generation/tools.py, never routed through the model
     as callable tools, so there is no tool-call loop here to cap
  6. Quota and the kill switch, checked before the call, atomically

Calls into `features.generation.quota` for (5) and (6) — a dependency from a
low-level seam into a feature, which looks backwards. It is: `generation`
(Build) is the only caller that exists in v1, and its data module is where
the plan puts the quotas/generations tables. Imported from the `quota`
submodule directly, not the package's `__init__.py` — that package re-exports
`build_experience`, which imports this module, so routing through the package
here would be circular. Future phases (intake, director, edit) call this same
seam and the same two functions through `features.generation`'s public
surface.
"""

import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, cast

import httpx
from pydantic import BaseModel, ValidationError

from config import config
from features.generation.quota import check_quota_and_kill_switch, log_generation
from lib.result import Err, Result, err, ok
from schema.json_schema import serialize_deterministically

Phase = Literal["intake", "director", "build", "edit"]


@dataclass(frozen=True, slots=True)
class Completion[T]:
    """The parsed value, plus whether it took the one repair retry to get
    there. A caller streaming scenes to a client is the reason this needs to
    survive past the seam rather than only reaching the `generations` log —
    it is the `repair` SSE event's one source of truth
    (docs/v1/plan/06-model-seam-and-build.md -> "7. Streaming to the client")."""

    value: T
    repaired: bool


_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT = httpx.Timeout(90.0, connect=10.0)


def _model_for_phase(phase: Phase) -> str:
    c = config()
    return {
        "intake": c.openrouter_model_intake,
        "director": c.openrouter_model_director,
        "build": c.openrouter_model_build,
        "edit": c.openrouter_model_edit,
    }[phase]


# Verified live against OpenRouter (2026-08): a schema carrying integer
# `minimum`/`maximum` or array `maxItems`/`minItems` makes every Anthropic-
# family route (Anthropic direct, Bedrock, Azure) reject the request outright
# with 400 `output_config.format.schema: ... not supported` — before the
# request ever reaches the model. `oneOf` (Pydantic's own encoding of a
# `discriminator`-tagged union, e.g. `Block.props`) fails the same way with
# "Schema type 'oneOf' is not supported". OpenAI's own models accept the full
# keyword set and `oneOf`, but "the seam must never assume [strict] held"
# (docs/v1/plan/06-model-seam-and-build.md), so these always get adjusted
# before anything goes over the wire, regardless of route.
#
# Pydantic still enforces every stripped constraint locally on the way back —
# `complete()`'s repair retry is exactly the backstop for a value that
# violates a bound the provider never saw. Renaming `oneOf` to `anyOf` is
# safe rather than lossy: every `BlockProps` variant requires its own
# `type` literal with `additionalProperties: false`, so no payload can ever
# satisfy two variants at once — "exactly one" and "at least one" coincide
# here.
_UNSUPPORTED_STRICT_KEYWORDS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minItems",
        "maxItems",
        # Sibling of `oneOf`/`anyOf` on a discriminated union — "For 'anyOf',
        # 'discriminator' is not supported" once `oneOf` above is renamed.
        # Each variant's own `type` literal still discriminates for the
        # model; this key only ever spoke to a validator that no longer sees
        # `oneOf` to attach it to.
        "discriminator",
    }
)


def _strip_unsupported_keywords(node: object) -> object:
    if isinstance(node, dict):
        out = {
            ("anyOf" if k == "oneOf" else k): _strip_unsupported_keywords(v)
            for k, v in node.items()
            if k not in _UNSUPPORTED_STRICT_KEYWORDS
        }
        # Both OpenAI's and Anthropic's strict mode require every key in
        # `properties` to also appear in `required` — a field with a Pydantic
        # default (`motion: Motion = "reveal"`, `region: Region | None =
        # None`) is exactly the kind of thing Pydantic's own JSON Schema
        # omits from `required`, and OpenAI rejects that outright: "'required'
        # is required to be ... including every key in properties." The model
        # still always emits a value for the key; only Python's own default
        # ever applies, and only when the field is genuinely absent from a
        # hand-authored fixture, not from a model response.
        properties = out.get("properties")
        if isinstance(properties, dict):
            out["required"] = list(properties.keys())
        return out
    if isinstance(node, list):
        return [_strip_unsupported_keywords(v) for v in node]
    return node


def _payload(
    model: str, system: str, user: str, schema: type[BaseModel]
) -> dict[str, object]:
    # Deterministic serialization (phase 01's helper, reused rather than a
    # second one) is the caching discipline that survives any route: a
    # re-ordered schema dump is a different prefix, and this is the one place
    # the schema becomes bytes in the request (docs/v1/ai-pipeline.md ->
    # "Prompt caching").
    json_schema = _strip_unsupported_keywords(
        json.loads(
            serialize_deterministically(
                schema.model_json_schema(ref_template="#/$defs/{model}")
            )
        )
    )
    return {
        "model": model,
        "stream": True,
        "stream_options": {"include_usage": True},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": json_schema,
            },
        },
    }


class _RawCompletion(BaseModel):
    content: str
    finish_reason: str | None
    model_id: str
    provider_route: str
    tokens_in: int
    tokens_out: int
    cached_tokens: int


async def _iter_sse_data(response: httpx.Response) -> AsyncIterator[dict[str, object]]:
    # Verified live against OpenRouter (2026-08): a single logical SSE event
    # can arrive as *multiple* consecutive `data:` lines — observed with
    # `openai/gpt-5-mini` on a long streamed delta — and the SSE spec says
    # those get concatenated (joined by `\n`) into one payload before
    # parsing. Treating every `data:` line as its own complete JSON object,
    # as this used to, parses a truncated fragment and raises
    # `json.JSONDecodeError: Unterminated string` — a crash, not a `Result`,
    # for a wire-format case that was always possible.
    buffer: list[str] = []

    def _flush() -> dict[str, object] | None:
        if not buffer:
            return None
        data = "\n".join(buffer)
        buffer.clear()
        if data == "[DONE]":
            return None
        return cast(dict[str, object], json.loads(data))

    async for line in response.aiter_lines():
        if line.startswith("data:"):
            buffer.append(line[len("data:") :].strip())
            continue
        if line == "":
            parsed = _flush()
            if parsed is not None:
                yield parsed
            continue
        # A non-`data:`, non-blank line (`event:`, `id:`, a comment) ends
        # nothing on its own — SSE events are blank-line-delimited.
    parsed = _flush()
    if parsed is not None:
        yield parsed


async def _stream_once(
    client: httpx.AsyncClient, payload: dict[str, object], model: str
) -> Result[_RawCompletion]:
    content_parts: list[str] = []
    finish_reason: str | None = None
    model_id = model
    provider_route = "openrouter"
    tokens_in = tokens_out = cached_tokens = 0

    try:
        async with client.stream(
            "POST",
            _ENDPOINT,
            json=payload,
            headers={"Authorization": f"Bearer {config().openrouter_api_key}"},
            timeout=_TIMEOUT,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                return err(
                    "upstream_unavailable",
                    f"openrouter {response.status_code}: {body[:200]!r}",
                )
            async for chunk in _iter_sse_data(response):
                if "model" in chunk:
                    model_id = cast(str, chunk["model"])
                if "provider" in chunk:
                    provider_route = cast(str, chunk["provider"])
                choices = cast(list[dict[str, object]], chunk.get("choices") or [])
                if choices:
                    choice = choices[0]
                    delta = cast(dict[str, object], choice.get("delta") or {})
                    piece = delta.get("content")
                    if isinstance(piece, str):
                        content_parts.append(piece)
                    fr = choice.get("finish_reason")
                    if isinstance(fr, str):
                        finish_reason = fr
                usage = chunk.get("usage")
                if isinstance(usage, dict):
                    tokens_in = cast(int, usage.get("prompt_tokens", tokens_in))
                    tokens_out = cast(int, usage.get("completion_tokens", tokens_out))
                    details = usage.get("prompt_tokens_details")
                    if isinstance(details, dict):
                        cached_tokens = cast(int, details.get("cached_tokens", 0))
    except httpx.HTTPError as e:
        return err("upstream_unavailable", f"{type(e).__name__}: {e}")

    return ok(
        _RawCompletion(
            content="".join(content_parts),
            finish_reason=finish_reason,
            model_id=model_id,
            provider_route=provider_route,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cached_tokens=cached_tokens,
        )
    )


def _detect_refusal(raw: _RawCompletion) -> str | None:
    """The field that says "declined" differs by provider, and a decline
    arrives as a *successful* HTTP response — this is the one place that
    matters, so every caller gets it for free (docs/v1/ai-pipeline.md ->
    "Repair and refusal")."""
    if raw.finish_reason == "content_filter":
        return "content_filter"
    if not raw.content.strip():
        return "empty_response"
    return None


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


async def complete[T: BaseModel](
    *,
    phase: Phase,
    schema: type[T],
    system: str,
    user: str,
    owner_id: str,
    experience_id: str,
) -> Result[Completion[T]]:
    quota = await check_quota_and_kill_switch(owner_id)
    if isinstance(quota, Err):
        return quota

    model = _model_for_phase(phase)
    start = time.monotonic()
    repaired = False
    error_class: str | None = None
    parsed: T | None = None
    raw: _RawCompletion | None = None
    calls = 0

    async with httpx.AsyncClient() as client:
        payload = _payload(model, system, user, schema)
        first = await _stream_once(client, payload, model)
        calls += 1
        if isinstance(first, Err):
            error_class = first.error.code
        else:
            raw = first.value
            refusal = _detect_refusal(raw)
            if refusal:
                error_class = "refused"
            else:
                try:
                    parsed = schema.model_validate_json(_strip_code_fence(raw.content))
                except ValidationError as e:
                    # One repair call: the scene, the specific errors, and
                    # nothing else — never a second attempt after this.
                    repair_user = (
                        f"Your previous response failed schema validation.\n\n"
                        f"Validation errors:\n{e}\n\n"
                        f"Your previous response was:\n{raw.content}\n\n"
                        f"Return corrected JSON conforming to the schema. "
                        f"Output only the JSON, nothing else."
                    )
                    repair_payload = _payload(model, system, repair_user, schema)
                    second = await _stream_once(client, repair_payload, model)
                    calls += 1
                    if isinstance(second, Err):
                        error_class = second.error.code
                    else:
                        raw = second.value
                        refusal = _detect_refusal(raw)
                        if refusal:
                            error_class = "refused"
                        else:
                            try:
                                parsed = schema.model_validate_json(
                                    _strip_code_fence(raw.content)
                                )
                                repaired = True
                            except ValidationError:
                                error_class = "repair_exhausted"

    duration_ms = int((time.monotonic() - start) * 1000)
    await log_generation(
        owner_id=owner_id,
        experience_id=experience_id,
        phase=phase,
        model_id=raw.model_id if raw else model,
        provider_route=raw.provider_route if raw else "openrouter",
        tokens_in=raw.tokens_in if raw else 0,
        tokens_out=raw.tokens_out if raw else 0,
        cached_tokens=raw.cached_tokens if raw else 0,
        calls=calls,
        repaired=repaired,
        error_class=error_class,
        duration_ms=duration_ms,
    )

    if parsed is not None:
        return ok(Completion(value=parsed, repaired=repaired))
    if error_class == "refused":
        return err("refused", "the model declined the request")
    if error_class == "repair_exhausted":
        return err("repair_exhausted", "invalid after one repair attempt")
    return err("upstream_unavailable", error_class or "unknown failure")
