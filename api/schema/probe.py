"""A throwaway model that exists only to prove the codegen chain.

Phase 00 has to stand up Pydantic -> JSON Schema -> TypeScript types + a Zod
validator and prove it regenerates with no diff. Discovering that the chain
cannot express a nested tagged union while *designing* the real IR is the worst
possible time, so the shape is proved against something disposable first.

`Probe` therefore mirrors the one structural property phase 01 depends on and
nothing else: **a discriminated union nested inside an object, never at the
root** — the shape strict structured-output validators handle cleanly
(docs/coderules/python.md).

ponytail: delete this file in phase 01, the moment `Scene` replaces it in the
codegen registry. It is scaffolding, not schema.
"""

from typing import Annotated, Literal

from pydantic import Field

from schema.base import Schema


class ProbeHeadline(Schema):
    kind: Literal["headline"]
    # Character caps do not survive into structured output — implementations
    # widely ignore minLength/maxLength. Kept anyway: they cost nothing and
    # they are what does the rejecting on the way back in.
    text: str = Field(max_length=60)


class ProbeBody(Schema):
    kind: Literal["body"]
    text: str = Field(max_length=240)


ProbeBlock = Annotated[ProbeHeadline | ProbeBody, Field(discriminator="kind")]


class Probe(Schema):
    id: str
    blocks: list[ProbeBlock]
