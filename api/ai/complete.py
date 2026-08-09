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
from collections import Counter
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

# Verified live (2026-08): with no cap, a single Build scene ran 32k output
# tokens over 7.4 minutes — a degenerate generation (a known LLM failure
# mode, the model stuck producing filler instead of stopping), not a
# repair or a retry. httpx's timeout does not catch this: it is a per-read
# timeout, and a slowly trickling stream never trips it no matter the
# total duration. Every legitimate scene or outline seen so far is under
# 5k tokens; 8000 leaves real headroom while still cutting a runaway off
# early — the same "cap it, denial-of-wallet is the same class of problem
# as unbounded repair" reasoning docs/security/prompt-injection.md already
# applies to tool calls, extended here to output length.
_MAX_OUTPUT_TOKENS = 8000

# Verified live (2026-08, phase 08): every model behind `_model_for_phase`
# is a reasoning model, and OpenRouter bills its hidden reasoning tokens out
# of the *same* `max_tokens` budget as the visible completion — a trivial
# 40-word request burned 256 reasoning tokens and hit `finish_reason:
# length` with `content: null`, zero visible output, at the default
# setting. `reasoning.max_tokens` does NOT cap this (set to 50, the model
# still spent 256 and produced nothing); `reasoning.effort: "minimal"` is
# the lever that actually works — same run, 0 reasoning tokens, full
# content, `finish_reason: stop`, a quarter of the cost.
#
# This is very likely what the 32k-token runaway above actually was, and a
# quieter version of it is the more likely explanation for CI's
# `repair_exhausted` failures on the golden briefs (docs/v1/plan/
# 06-model-seam-and-build.md): on an unlucky call, reasoning silently eats
# a variable, sometimes large slice of `_MAX_OUTPUT_TOKENS`, and Build's
# `strict: true` structured output has to fit the rest — the smaller that
# rest gets, the likelier a scene runs out of room mid-structure.
#
# Every call through this seam fills an already-fully-specified schema —
# Intake selects and splits, Director sequences a fixed set of intents,
# Build writes bounded copy, Edit patches one field — none of it is
# open-ended problem solving reasoning effort is for. If a future phase
# genuinely needs it, that is a `_model_for_phase`-shaped decision (a
# per-phase override), not a reason to leave every phase paying the tax
# today for a benefit none of them use.
_REASONING = {"effort": "minimal"}


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
        # Supported, and that was the problem. The provider honours `maxLength`
        # during constrained decoding by *cutting the string off* at the bound,
        # so an over-long headline came back structurally valid and garbled —
        # "Tracepoint: API observ-" — which Pydantic accepts, every post-build
        # check passes, and repair never sees. Silently shipping garbled copy is
        # strictly worse than failing (docs/v1/plan/06-model-seam-and-build.md).
        #
        # Stripping the bounds restores what docs/coderules/typescript.md always
        # described: the wire schema carries the *shape*, Pydantic enforces the
        # *lengths* on the way back, and the repair retry is the backstop. That
        # only became affordable once the discriminator moved to the front of
        # each variant (`schema/json_schema.py`) — before that the model wrote a
        # block's text before choosing its type, overshot every cap, and every
        # scene died in repair. With `type` first it writes to the right block
        # and lands inside the caps on its own: measured 8 of 9 scenes valid on
        # the first attempt with no length constraint on the wire at all.
        "maxLength",
        "minLength",
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
        "max_tokens": _MAX_OUTPUT_TOKENS,
        "reasoning": _REASONING,
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


def _sse_payload(line: str) -> str | None:
    """The JSON text of one SSE `data:` line — `None` for anything else
    (`event:`, `id:`, a comment, a blank)."""
    stripped = line.rstrip("\r").strip()
    if not stripped.startswith("data:"):
        return None
    return stripped[len("data:") :].strip() or None


async def _iter_sse_data(response: httpx.Response) -> AsyncIterator[dict[str, object]]:
    """Frames the stream on `\\n` — deliberately NOT `response.aiter_lines()`.

    httpx splits lines on `str.splitlines()` semantics, whose separator set
    is `\\n\\r\\x0b\\x0c\\x1c\\x1d\\x1e\\x85\\u2028\\u2029`
    (httpx/_decoders.py, `LineDecoder`). Six of those are not SSE line
    terminators, and three — `\\x85`, `\\u2028`, `\\u2029` — are legal
    *unescaped* inside a JSON string, which JavaScript's `JSON.stringify`
    (what an OpenAI-compatible gateway serializes with) does not escape. So
    a model that writes one of them into its copy splits its own `data:`
    payload in half on the way in, and the halves parse as truncated JSON.

    Verified live: this is what `JSONDecodeError: Unterminated string` was,
    and it killed a whole build rather than one scene, because the raise
    escaped `_stream_once`'s `except httpx.HTTPError` entirely.
    `test_complete.py` pins all three characters.

    Framing on `\\n` alone is safe in a way `splitlines()` is not: a raw
    `\\n` or `\\r` *cannot* appear inside a JSON string — JSON requires both
    escaped — so no payload can contain its own delimiter. One `data:` line
    carries one whole JSON object, which is the shape every
    OpenAI-compatible stream emits.
    """
    buffer = ""
    async for chunk in response.aiter_text():
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            data = _sse_payload(line)
            if data is None:
                continue
            if data == "[DONE]":
                return
            yield cast(dict[str, object], json.loads(data))

    # A final event with no trailing newline. Rare, but dropping it would
    # silently lose the usage chunk that carries `cached_tokens`.
    data = _sse_payload(buffer)
    if data is not None and data != "[DONE]":
        yield cast(dict[str, object], json.loads(data))


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
    # `JSONDecodeError` belongs here for the same reason `HTTPError` does: a
    # malformed chunk is the upstream misbehaving, which is an expected
    # failure of an external boundary, not a bug in this process (rule 3,
    # and rule 2 — model output is external input). Leaving it to raise is
    # what turned one bad character into a dead build instead of one failed
    # scene, and it skipped `log_generation` on the way out, so the call was
    # billed and unrecorded.
    except (httpx.HTTPError, json.JSONDecodeError) as e:
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


def _repair_budget(error: ValidationError) -> int:
    """How many repair calls this failure is worth.

    One, except for a failure where *every* error is a length overshoot, which
    gets two. Measured 2026-08-09: once the discriminator moved to the front of
    each variant and the caps reached the prompt, the entire remaining failure
    tail was `string_too_long` on a single field — copy the model wrote well and
    slightly too long. That is the cheapest repair there is (shorten one string,
    change nothing else) and the likeliest to land on a second try.

    Everything else keeps the original budget of one, and deliberately: a
    response that is not JSON, or that is missing a required field, is a
    different kind of wrong, and a third call at it is the unbounded-retry
    denial-of-wallet this cap exists to prevent
    (docs/security/prompt-injection.md).
    """
    kinds = {e["type"] for e in error.errors()}
    return 2 if kinds and kinds <= {"string_too_long", "string_too_short"} else 1


def _repair_prompt(error: ValidationError, previous: str) -> str:
    """Surgical on purpose. Told only to "return corrected JSON", the model
    rewrites the whole object and regresses fields that were already fine —
    measured 2026-08-09: a repair shortened an over-long headline from 66 to 48
    characters and, in the same response, grew a body that had been valid at 197
    to 276, failing again on a field the first attempt got right. A repair that
    can break what it was not asked to touch is a coin flip, not a backstop."""
    return (
        f"Your previous response failed schema validation.\n\n"
        f"Validation errors:\n{error}\n\n"
        f"Your previous response was:\n{previous}\n\n"
        f"Return the same JSON with ONLY the fields named in those errors "
        f"changed. Every other field must come back byte-identical — do not "
        f"reword, reformat, or improve anything the errors do not mention. "
        f"Output only the JSON, nothing else."
    )


def _describe(error: ValidationError) -> str:
    """Which fields failed and how — never what they contained.

    `repair_exhausted` used to discard this entirely, and that is most of why
    the truncation defect stayed invisible: the one code path that knew exactly
    what was wrong with a scene threw the answer away and returned "invalid
    after one repair attempt". Reconstructing it meant reproducing calls by
    hand outside the seam, twice, in two different sessions.

    `error_type at path` only. Pydantic's `errors()` carries an `input` key
    holding the offending value, which here is the customer's generated copy —
    that never reaches a log or an error string
    (docs/security/tenancy-and-data.md). Types and locations are enough to say
    "eleven `string_too_long` on `eyebrow.text`", which is the sentence that
    would have ended this in one reading.
    """
    seen = Counter(
        f"{e['type']} at {'.'.join(str(p) for p in e['loc'] if not isinstance(p, int))}"
        for e in error.errors()
    )
    return "; ".join(
        f"{name} x{n}" if n > 1 else name for name, n in seen.most_common(5)
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
    repair_failure: str | None = None
    parsed: T | None = None
    raw: _RawCompletion | None = None
    calls = 0

    async with httpx.AsyncClient() as client:
        attempt = _payload(model, system, user, schema)
        while True:
            response = await _stream_once(client, attempt, model)
            calls += 1
            if isinstance(response, Err):
                error_class = response.error.code
                break

            raw = response.value
            if _detect_refusal(raw):
                error_class = "refused"
                break

            try:
                parsed = schema.model_validate_json(_strip_code_fence(raw.content))
                repaired = calls > 1
                break
            except ValidationError as invalid:
                # Evaluated per failure, so a run that starts as a length
                # overshoot and turns structural drops back to one repair
                # rather than inheriting the larger budget.
                if calls > _repair_budget(invalid):
                    error_class = "repair_exhausted"
                    repair_failure = _describe(invalid)
                    break
                attempt = _payload(
                    model, system, _repair_prompt(invalid, raw.content), schema
                )

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
        detail = f": {repair_failure}" if repair_failure else ""
        return err("repair_exhausted", f"invalid after one repair attempt{detail}")
    return err("upstream_unavailable", error_class or "unknown failure")
