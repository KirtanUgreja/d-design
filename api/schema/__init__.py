"""The Pydantic source of truth for the whole system.

This package has no TypeScript counterpart. `web` consumes generated types and
a generated Zod validator; creating a hand-written schema on the TypeScript
side is the drift this whole arrangement exists to prevent
(docs/coderules/structure.md, docs/coderules/python.md).

`EXPORTED` is the codegen's input. A model listed here is emitted into
`web/src/schema/` by `scripts/export_schema.py`; a model not listed here stays
inside Python. Adding a row is how a shape becomes part of the contract.
"""

from pydantic import BaseModel

from schema.probe import Probe

EXPORTED: dict[str, type[BaseModel]] = {
    "Probe": Probe,
}

__all__ = ["EXPORTED", "Probe"]
