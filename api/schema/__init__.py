"""The Pydantic source of truth for the whole system, and the catalog every
later phase reads before writing something that already exists.

This package has no TypeScript counterpart. `web` consumes generated types and
a generated Zod validator; creating a hand-written schema on the TypeScript
side is the drift this whole arrangement exists to prevent
(docs/coderules/structure.md, docs/coderules/python.md).

`EXPORTED` is the codegen's input. A model listed here is emitted into
`web/src/schema/` by `web/scripts/generate-schema.mjs`; a model not listed here
stays inside Python. Adding a row is how a shape becomes part of the contract —
`Experience` pulls in `Scene` and every block type as `$defs`, so most of the
tree below is exported without being listed twice.
"""

from pydantic import BaseModel

from schema.brief import Brief, InterviewStep, Question
from schema.experience import Asset, BrandKit, Experience
from schema.outline import Outline
from schema.overflow import BlockExtent, OverflowReport, SceneOverflow
from schema.patch import BlockPatch, EditResult
from schema.scene import Block, Scene

EXPORTED: dict[str, type[BaseModel]] = {
    "Experience": Experience,
    "Scene": Scene,
    "Block": Block,
    "Asset": Asset,
    "BrandKit": BrandKit,
    "Brief": Brief,
    # `InterviewStep` pulls `Question` in as a `$def`, the same way `Experience`
    # pulls in `Scene` — listed anyway, because the Intake screen renders a
    # question on its own and a shape web imports by name should be a row here
    # rather than something reached through another model's `$defs`.
    "InterviewStep": InterviewStep,
    "Question": Question,
    "Outline": Outline,
    # `OverflowReport` pulls the other two in as `$defs`; all three are listed
    # because the banner renders a `SceneOverflow` on its own and a shape web
    # imports by name should be a row here rather than reached through another
    # model's `$defs`.
    "OverflowReport": OverflowReport,
    "SceneOverflow": SceneOverflow,
    "BlockExtent": BlockExtent,
    "BlockPatch": BlockPatch,
    "EditResult": EditResult,
}

__all__ = [
    "EXPORTED",
    "Asset",
    "Block",
    "BlockPatch",
    "BrandKit",
    "Brief",
    "EditResult",
    "Experience",
    "InterviewStep",
    "Outline",
    "Question",
    "Scene",
]
