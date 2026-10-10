"""The model seam — the only module that calls a model.

docs/v4/engine.md -> "The model seam". Plain httpx to OpenRouter's
OpenAI-compatible endpoint: no SDK, no framework. Ported from v3's
``ai/complete.py`` with its three bugs fixed:

- the repair path crashed on an unbound ``raw`` when the first answer was not
  JSON at all, which is the case it exists for;
- a schema-invalid answer was sent back to the model as ``""``, so the repair
  could not see what it had written;
- repairs were counted on the seam instance, so a whole deck got one.

Here a repair is per call, it carries the model's real previous answer, and the
seam is async so slides can be composed in parallel.

Logging rule: the ledger records ids, sizes, timings and cost. Never a prompt,
never an answer (docs/security/operations.md).
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError

from engine.models import LedgerEntry, Stage
from lib.result import Err, Ok, Result, err, ok

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# One corrective pass per call, then fail visibly. An unbounded loop is a token
# furnace, and the model never decides how many times this runs.
MAX_REPAIRS = 1
IMAGE_VERSION = "image.v1"
MAX_IMAGE_B64 = 16_000_000  # ~12 MB decoded: far above any real slide image
# Transport retries for 429 and 5xx only. Bounded for the same reason.
MAX_TRANSPORT_RETRIES = 2
# 402 too: on a low balance the gateway refuses a call while others are in
# flight, and it clears when they finish (2026-10-09).
RETRYABLE = frozenset({402, 429, 500, 502, 503, 504})

ReasoningEffort = Literal["minimal", "low", "medium", "high"]
FailKind = Literal["transport", "truncated", "refused"]


@dataclass(frozen=True)
class ModelError:
    """An expected model-call failure."""

    kind: Literal[
        "transport", "truncated", "refused", "invalid", "repair_exhausted", "no_key", "budget"
    ]
    detail: str


@dataclass(frozen=True)
class Citation:
    url: str
    title: str
    content: str


@dataclass(frozen=True)
class Reply:
    """What a model said: its text, plus any web-search citations."""

    text: str
    citations: tuple[Citation, ...] = ()
    images: tuple[str, ...] = ()  # data: URLs, from an image-output model


class Transport(Protocol):
    """The network boundary. ``httpx.AsyncClient`` satisfies it; tests stub it."""

    async def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response: ...


# --- the wire shapes we read. Parsed once, here, at entry (rule 2). ----------


class _UrlCitation(BaseModel):
    url: str = ""
    title: str = ""
    content: str = ""


class _Annotation(BaseModel):
    type: str = ""
    url_citation: _UrlCitation | None = None


class _ImageUrl(BaseModel):
    url: str = ""


class _Image(BaseModel):
    image_url: _ImageUrl = Field(default_factory=_ImageUrl)


class _Message(BaseModel):
    content: str | None = None
    refusal: str | None = None
    annotations: list[_Annotation] = Field(default_factory=list)
    images: list[_Image] = Field(default_factory=list)  # image output (phase 39)


class _Choice(BaseModel):
    message: _Message
    finish_reason: str | None = None


class _PromptDetails(BaseModel):
    cached_tokens: int = 0


class _CompletionDetails(BaseModel):
    reasoning_tokens: int = 0


class _Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    prompt_tokens_details: _PromptDetails | None = None
    completion_tokens_details: _CompletionDetails | None = None


class _ChatResponse(BaseModel):
    choices: list[_Choice] = Field(min_length=1)
    usage: _Usage = Field(default_factory=_Usage)
    provider: str = ""


# --- helpers -----------------------------------------------------------------


def _gateway_error(response: httpx.Response) -> str:
    """The gateway's own error code and message, if the body carries one:
    "402 Insufficient credits". Never the prompt or the answer."""
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError):
        return ""
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return ""
    return f"{error.get('code', '')} {str(error.get('message', ''))[:120]}".strip()


def strict_schema(schema: object) -> object:
    """Make a JSON Schema strict for providers that require it.

    Strict structured output rejects an object without
    ``additionalProperties: false`` or with a property missing from
    ``required``. Pydantic emits neither for optional fields, so both are added
    here. Our own ``model_validate`` still enforces true optionality.
    """
    if isinstance(schema, dict):
        out: dict[str, object] = {}
        for key, value in schema.items():
            if key == "$defs" and isinstance(value, dict):
                out[key] = {k: strict_schema(v) for k, v in value.items()}
            else:
                out[key] = strict_schema(value)
        if schema.get("type") == "object":
            out.setdefault("additionalProperties", False)
            props = schema.get("properties")
            if isinstance(props, dict):
                declared = schema.get("required")
                required = set(declared) if isinstance(declared, list) else set()
                required.update(props.keys())
                out["required"] = sorted(required)
        return out
    if isinstance(schema, list):
        return [strict_schema(v) for v in schema]
    return schema


_FENCE = re.compile(r"```([a-zA-Z]*)[ \t]*\n(.*?)```", re.DOTALL)


def parse_fenced(text: str, *langs: str) -> Result[dict[str, str], str]:
    """Pull one fenced block per language out of a text answer.

    Slide HTML travels as fenced ``html`` and ``css`` blocks, never as strings
    inside JSON: escaping wastes tokens and breaks, and format constraints
    reduce diversity (docs/findings.md -> Model behaviour).
    """
    found: dict[str, str] = {}
    for lang, body in _FENCE.findall(text):
        key = lang.lower()
        if key in langs and key not in found:
            found[key] = body.strip()
    missing = [lang for lang in langs if lang not in found]
    if missing:
        return err(f"answer has no fenced block for: {', '.join(missing)}")
    return ok(found)


# The slowest call measured is about a minute. A stalled connection on a 300 s
# timeout, with two retries, held a deck for 15 minutes (2026-10-01).
TIMEOUT_S = 120.0


def _default_transport() -> Transport:
    return httpx.AsyncClient(timeout=TIMEOUT_S)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class Seam:
    """The one model call site.

    Everything it needs is injected — transport, key, clock, sleep — so tests
    never touch the network and the engine never reads the environment.
    """

    api_key: str
    transport: Transport = field(default_factory=_default_transport)
    base_url: str = OPENROUTER_URL
    ledger: list[LedgerEntry] = field(default_factory=list)
    deck_id: str = ""
    now: Callable[[], datetime] = _utcnow
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    # Asked before every call, retries and repairs included. Anything that
    # grants fails closed: a guard that raises refuses the call (rule 10).
    allow: Callable[[], bool] | None = None
    # model -> the one provider it may run on (settings.MODEL_PROVIDERS).
    providers: Mapping[str, str] = field(default_factory=dict)

    @property
    def spent_usd(self) -> float:
        return sum(entry.cost_usd for entry in self.ledger)

    async def complete_json[T: BaseModel](
        self,
        stage: Stage,
        schema: type[T],
        *,
        system: str,
        user: str,
        model: str,
        prefix: str | None = None,
        prompt_version: str = "",
        max_tokens: int = 8000,
        reasoning: ReasoningEffort | None = None,
        slide_id: str | None = None,
        images: tuple[str, ...] = (),
    ) -> Result[T, ModelError]:
        """One call, validated against ``schema``, with one repair."""

        def parse(reply: Reply) -> Result[T, str]:
            try:
                return ok(schema.model_validate(json.loads(reply.text)))
            except (ValidationError, json.JSONDecodeError) as exc:
                return err(str(exc)[:2000])

        response_format: dict[str, object] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": strict_schema(schema.model_json_schema()),
            },
        }
        return await self._with_repair(
            stage,
            parse,
            system=system,
            user=user,
            model=model,
            prefix=prefix,
            prompt_version=prompt_version,
            max_tokens=max_tokens,
            reasoning=reasoning,
            slide_id=slide_id,
            extra={"response_format": response_format},
            images=images,
        )

    async def complete_text[T](
        self,
        stage: Stage,
        parse: Callable[[Reply], Result[T, str]],
        *,
        system: str,
        user: str,
        model: str,
        prefix: str | None = None,
        prompt_version: str = "",
        max_tokens: int = 8000,
        reasoning: ReasoningEffort | None = None,
        slide_id: str | None = None,
        tools: list[dict[str, object]] | None = None,
        images: tuple[str, ...] = (),
    ) -> Result[T, ModelError]:
        """One call whose answer we parse ourselves, with one repair.

        ``tools`` carries server tools only (``openrouter:web_search``). The
        model gets no tool with side effects. ``images`` are data URLs the
        model looks at with the user message (our own screenshots, never a
        user's file).
        """
        extra: dict[str, object] = {"tools": tools} if tools else {}
        return await self._with_repair(
            stage,
            parse,
            images=images,
            system=system,
            user=user,
            model=model,
            prefix=prefix,
            prompt_version=prompt_version,
            max_tokens=max_tokens,
            reasoning=reasoning,
            slide_id=slide_id,
            extra=extra,
        )

    async def complete_image(
        self,
        prompt: str,
        *,
        model: str,
        aspect: str,
        slide_id: str | None = None,
    ) -> Result[bytes, ModelError]:
        """One generated image, as the bytes the model returned. Only an inline
        data: URL is accepted: we never fetch a URL a model hands us. No repair:
        a failed image becomes a quiet field, never a second charge."""
        if not self.api_key:
            return err(ModelError("no_key", "OPENROUTER_API_KEY is not set"))
        refused = self._refused()
        if refused is not None:
            return err(refused)
        body: dict[str, object] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "image_config": {"aspect_ratio": aspect},
            "usage": {"include": True},
        }
        if self.deck_id:
            body["session_id"] = self.deck_id
        sent = await self._send(
            body,
            stage="image",
            model=model,
            prompt_version=IMAGE_VERSION,
            slide_id=slide_id,
            attempt=1,
        )
        if isinstance(sent, Err):
            return sent
        for url in sent.value.images:
            head, _, data = url.partition(",")
            if head.startswith("data:image/") and head.endswith(";base64") and data:
                if len(data) > MAX_IMAGE_B64:
                    break
                try:
                    return ok(base64.b64decode(data, validate=True))
                except ValueError:
                    break
        self.ledger[-1].ok = False
        self.ledger[-1].error_kind = "invalid"
        return err(ModelError("invalid", "no inline image in the answer"))

    async def _with_repair[T](
        self,
        stage: Stage,
        parse: Callable[[Reply], Result[T, str]],
        *,
        system: str,
        user: str,
        model: str,
        prefix: str | None,
        prompt_version: str,
        max_tokens: int,
        reasoning: ReasoningEffort | None,
        slide_id: str | None,
        extra: dict[str, object],
        images: tuple[str, ...] = (),
    ) -> Result[T, ModelError]:
        if not self.api_key:
            return err(ModelError("no_key", "OPENROUTER_API_KEY is not set"))

        # The stable prefix goes first and is marked cacheable, so the calls of
        # one deck reuse it (rules -> theme -> exemplars).
        system_content: object = system
        if prefix:
            system_content = [
                {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": system},
            ]
        user_content: object = user
        if images:
            user_content = [
                {"type": "text", "text": user},
                *({"type": "image_url", "image_url": {"url": u}} for u in images),
            ]
        messages: list[dict[str, object]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]
        body: dict[str, object] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "usage": {"include": True},
            **extra,
        }
        if reasoning is not None:
            body["reasoning"] = {"effort": reasoning}
        if model in self.providers:
            # Pinned, no fallback: a call billed to the owner's own key never
            # silently moves to OpenRouter's credit.
            body["provider"] = {"only": [self.providers[model]], "allow_fallbacks": False}
        if self.deck_id:
            body["session_id"] = self.deck_id

        problem = ""
        for attempt in range(1, MAX_REPAIRS + 2):
            refused = self._refused()
            if refused is not None:
                return err(refused)
            sent = await self._send(
                body,
                stage=stage,
                model=model,
                prompt_version=prompt_version,
                slide_id=slide_id,
                attempt=attempt,
            )
            if isinstance(sent, Err):
                return sent
            reply = sent.value
            parsed = parse(reply)
            if isinstance(parsed, Ok):
                return parsed
            problem = parsed.error
            self.ledger[-1].ok = False
            self.ledger[-1].error_kind = "invalid"
            # The repair carries what the model actually wrote, and why it failed.
            messages.append({"role": "assistant", "content": reply.text})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous answer was rejected. "
                        f"Problem: {problem}\n"
                        "Answer again in the required format, fixing only that."
                    ),
                }
            )
        return err(ModelError("repair_exhausted", f"still invalid after repair: {problem}"))

    def _refused(self) -> ModelError | None:
        if self.allow is None:
            return None
        try:
            allowed = self.allow()
        except Exception as exc:  # any failure of the check is a refusal
            return ModelError("budget", f"the budget check failed: {type(exc).__name__}")
        return None if allowed else ModelError("budget", "the deck's budget is spent")

    async def _send(
        self,
        body: dict[str, object],
        *,
        stage: Stage,
        model: str,
        prompt_version: str,
        slide_id: str | None,
        attempt: int,
    ) -> Result[Reply, ModelError]:
        """One HTTP exchange, with bounded backoff, and its ledger entry."""
        started = time.monotonic()
        entry = LedgerEntry(
            at=self.now(),
            deck_id=self.deck_id,
            stage=stage,
            slide_id=slide_id,
            model=model,
            prompt_version=prompt_version,
            attempt=attempt,
        )
        self.ledger.append(entry)

        def fail(kind: FailKind, detail: str) -> Err[ModelError]:
            entry.ok = False
            entry.error_kind = kind
            entry.latency_ms = int((time.monotonic() - started) * 1000)
            return err(ModelError(kind, detail))

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        response: httpx.Response | None = None
        last = "no attempt"
        for retry in range(MAX_TRANSPORT_RETRIES + 1):
            try:
                response = await self.transport.post(self.base_url, json=body, headers=headers)
            except httpx.HTTPError as exc:
                response = None
                last = type(exc).__name__
            else:
                if response.status_code not in RETRYABLE:
                    break
                last = f"HTTP {response.status_code}"
            if retry < MAX_TRANSPORT_RETRIES:
                await self.sleep(2.0 * (retry + 1))
        if response is not None:
            entry.http_status = response.status_code
            entry.error_code = _gateway_error(response)
        if response is None or response.status_code != 200:
            status = last if response is None else f"HTTP {response.status_code}"
            return fail("transport", f"model endpoint failed: {status} {entry.error_code}")

        try:
            data = _ChatResponse.model_validate(response.json())
        except (ValidationError, json.JSONDecodeError) as exc:
            entry.error_code = entry.error_code or "shape"
            return fail("transport", f"unexpected response shape: {str(exc)[:300]}")

        usage = data.usage
        entry.provider = data.provider
        entry.input_tokens = usage.prompt_tokens
        entry.output_tokens = usage.completion_tokens
        entry.cost_usd = usage.cost
        if usage.prompt_tokens_details is not None:
            entry.cached_tokens = usage.prompt_tokens_details.cached_tokens
        if usage.completion_tokens_details is not None:
            entry.reasoning_tokens = usage.completion_tokens_details.reasoning_tokens
        entry.latency_ms = int((time.monotonic() - started) * 1000)

        choice = data.choices[0]
        # A cut-off or refused answer is a typed failure. It is never parsed:
        # half an answer that happens to validate is the worst outcome.
        if choice.finish_reason == "length":
            return fail("truncated", "the answer hit max_tokens")
        if choice.message.refusal or choice.finish_reason == "content_filter":
            return fail("refused", "the model refused")
        images = tuple(i.image_url.url for i in choice.message.images if i.image_url.url)
        if not choice.message.content and not images:
            entry.error_code = entry.error_code or f"empty:{choice.finish_reason or ''}"
            return fail("transport", "the answer was empty")

        citations = tuple(
            Citation(a.url_citation.url, a.url_citation.title, a.url_citation.content)
            for a in choice.message.annotations
            if a.type == "url_citation" and a.url_citation is not None
        )
        return ok(Reply(choice.message.content or "", citations, images))
