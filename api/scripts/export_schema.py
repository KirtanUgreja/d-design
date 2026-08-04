"""Emit the JSON Schema for every model in the codegen registry, to stdout.

This is one half of the chain that makes "one source of truth" a fact across a
language boundary. The other half lives in `web/scripts/generate-schema.mjs`,
which turns this output into TypeScript types and a Zod validator and fails on
a diff.

The JSON Schema is a pipe, never a checked-in file someone maintains. The
model's own structured-output constraint takes a different route entirely —
`model_json_schema()` called in-process at the seam — so it has nowhere to
travel to and no chance to go stale (docs/coderules/python.md).

    uv run python scripts/export_schema.py
"""

import json
import sys

from schema import EXPORTED


def export() -> dict[str, object]:
    return {
        name: model.model_json_schema(ref_template="#/$defs/{model}")
        for name, model in sorted(EXPORTED.items())
    }


if __name__ == "__main__":
    json.dump(export(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
