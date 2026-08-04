"""The model's structured-output constraint, deterministically serialized.

`SCENE_JSON_SCHEMA` sits in the Build phase's cached prefix, and a re-ordered
JSON dump is a different prefix — which silently costs 10x on the largest
phase (docs/v1/ai-pipeline.md -> prompt caching). Sorting keys here, once,
means every call site gets a stable prefix without having to remember why.

It never leaves the process. The seam is in the same codebase as the schema,
so the constraint the model receives and the validator that checks the
response are the same object — the one thing the Python move made simpler
rather than harder (docs/coderules/python.md).
"""

import json
from typing import Final

from schema.experience import Experience

SCENE_JSON_SCHEMA: Final[dict[str, object]] = Experience.model_json_schema(
    ref_template="#/$defs/{model}"
)


def serialize_deterministically(schema: dict[str, object]) -> str:
    """Stable bytes for a stable prefix. Called at the point of use rather than
    cached as a string, since `dict` equality (not string equality) is what the
    round-trip tests actually need."""
    return json.dumps(schema, sort_keys=True, separators=(",", ":"))
