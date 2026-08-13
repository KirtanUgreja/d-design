"""The model seam — the only place a model is called.

patterns.md rule 6: every call to a model goes through one module. The seam is
a function, a Pydantic model, and a model_validate. It owns the five things
that must not be reimplemented per call site: model_validate of the response,
the single repair retry, refusal normalization, the metadata log, and the
tool-call caps.

The pipeline has no preferred model vendor — only a preferred interface. The
route and model are parameters so per-phase model selection stays an eval
result rather than a conviction.

Phase 00 scope: the seam exists and a trivial call through it returns a
schema-valid result. The HTTP client and the metadata log land with the real
calls in phases 02-04.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeVar

from pydantic import BaseModel

from lib.result import Result, err

Phase = Literal["interview", "mapping", "slide", "critic"]

# The seam's single repair retry. One attempt, then fail visibly — an unbounded
# loop is a token furnace and the exact autonomy this pipeline does not have.
MAX_REPAIR_RETRIES = 1

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ModelError:
    """An expected model-call failure: refusal, malformed output, transport."""

    kind: Literal["refused", "invalid", "transport", "repair_exhausted"]
    detail: str


@dataclass
class CallStats:
    calls: int = 0
    repairs: int = 0
    latency_ms: int = 0
    model: str = ""
    route: str = ""


@dataclass
class Seam:
    """The one model call site. Injected with a transport so tests never hit
    the network."""

    # ponytail: a callable transport standing in for the httpx client, so the
    # seam is testable without a network. The real httpx call lands in
    # phase 02 when the interview actually calls out.
    transport: object = field(default_factory=object)

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
        del phase, system, user, model, route  # transport lands in phase 02
        return err(ModelError("transport", "seam transport not wired yet"))


def make_seam() -> Seam:
    return Seam()
