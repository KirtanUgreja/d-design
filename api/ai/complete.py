"""The model seam — the only place a model is called.

patterns.md rule 6: every call to a model goes through one module. The seam is
a function, a Pydantic model, and a model_validate. It owns the five things
that must not be reimplemented per call site: model_validate of the response,
the single repair retry, refusal normalization, the metadata log, and the
tool-call caps.

The pipeline has no preferred model vendor — only a preferred interface. The
route and model are parameters so per-phase model selection stays an eval
result rather than a conviction.

Transport: plain httpx to an OpenAI-compatible endpoint (OpenRouter). No SDK,
no framework — a function, a Pydantic model, and a model_validate
(ai-stack.md -> "What is worth considering, and is not a framework").
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from lib.result import Result, err, ok

Phase = Literal["interview", "mapping", "slide", "critic"]

# The seam's single repair retry. One attempt, then fail visibly — an unbounded
# loop is a token furnace and the exact autonomy this pipeline does not have.
MAX_REPAIR_RETRIES = 1

# OpenRouter is the default route (backend.md -> "Model access"). The base URL
# is overridable for tests and for a future route switch.
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ModelError:
    """An expected model-call failure: refusal, malformed output, transport."""

    kind: Literal["refused", "invalid", "transport", "repair_exhausted"]
    detail: str


@dataclass
class CallStats:
    """Metadata log. No prompts, no outputs — tenancy-and-data.md.

    ``calls`` counts every HTTP attempt (including repairs); ``repairs`` counts
    the corrective re-sends. ``latency_ms`` is wall time for the whole call.
    """

    calls: int = 0
    repairs: int = 0
    latency_ms: int = 0
    model: str = ""
    route: str = ""


class Transport(Protocol):
    """The seam's network boundary. httpx.Client satisfies it; tests inject a
    stub."""

    def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response: ...


def _default_transport() -> Transport:
    # One module-level client, reused (python.md -> "One httpx.AsyncClient,
    # module-level, reused"). A client per call leaks connections.
    return httpx.Client(timeout=120.0)


@dataclass
class Seam:
    """The one model call site. Injected with a transport so tests never hit
    the network."""

    transport: Transport = field(default_factory=_default_transport)
    api_key: str = field(default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", ""))
    base_url: str = OPENROUTER_URL
    stats: CallStats = field(default_factory=CallStats)

    # Bounded loops stay here and stay bounded (patterns.md rule 6): one repair,
    # one call per phase. The model cannot change how many times this runs.
    def complete(
        self,
        phase: Phase,
        schema: type[T],
        system: str,
        user: str,
        model: str,
        route: str = "openrouter/auto",
    ) -> Result[T, ModelError]:
        """Call the model once and validate the response against ``schema``.

        The single repair retry re-sends the invalid output as corrective
        context. If the repair also fails, this returns repair_exhausted.
        """
        if not self.api_key:
            return err(ModelError("transport", "OPENROUTER_API_KEY is not set"))

        started = time.monotonic()
        # messages is a concrete list of OpenAI-format message dicts; typing it
        # keeps the append in the repair path typechecked instead of object.
        messages: list[dict[str, object]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        body: dict[str, object] = {
            "model": model,
            "messages": messages,
            # The schema is the structured-output constraint. Enforced by
            # model_validate on the response regardless of what the provider
            # does with strict: true (backend.md -> "It costs a guarantee").
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        }

        response = self._post(body)
        self.stats.calls += 1
        if response.status_code != 200:
            return err(
                ModelError(
                    "transport",
                    f"model endpoint returned {response.status_code}",
                )
            )

        try:
            raw = self._extract_json(response)
            value = schema.model_validate(raw)
        except (ValidationError, ValueError, KeyError) as exc:
            # The single repair retry: one corrective pass, then fail visibly.
            self.stats.repairs += 1
            if self.stats.repairs > MAX_REPAIR_RETRIES:
                return err(
                    ModelError(
                        "repair_exhausted",
                        f"model output invalid after {MAX_REPAIR_RETRIES} repairs: {exc}",
                    )
                )
            messages.append(
                {
                    "role": "assistant",
                    "content": str(raw) if isinstance(raw, str) else "",
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous response did not match the required schema. "
                        f"Validation error: {exc}. Return only valid JSON matching the schema."
                    ),
                }
            )
            retry = self._post(body)
            self.stats.calls += 1
            if retry.status_code != 200:
                return err(ModelError("transport", f"model endpoint returned {retry.status_code}"))
            try:
                raw = self._extract_json(retry)
                value = schema.model_validate(raw)
            except (ValidationError, ValueError, KeyError) as exc2:
                return err(
                    ModelError(
                        "repair_exhausted",
                        f"model output invalid after repair: {exc2}",
                    )
                )

        self.stats.latency_ms = int((time.monotonic() - started) * 1000)
        self.stats.model = model
        self.stats.route = route
        return ok(value)

    def _post(self, body: dict[str, object]) -> httpx.Response:
        return self.transport.post(
            self.base_url,
            json=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def _extract_json(self, response: httpx.Response) -> object:
        data = response.json()
        # OpenAI-compatible shape: choices[0].message.content is the JSON
        # string. Parse it — the model returns text, not an object.
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"unexpected model response shape: {exc}") from exc
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError as exc:
                raise ValueError(f"model returned non-JSON content: {exc}") from exc
        return content


def make_seam(transport: Transport | None = None) -> Seam:
    if transport is not None:
        return Seam(transport=transport)
    return Seam()
