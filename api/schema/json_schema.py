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
    round-trip tests actually need.

    Deterministic, but no longer plain `sort_keys=True` — see `_ordered`.
    """
    return json.dumps(_ordered(schema), separators=(",", ":"))


def _ordered(node: object) -> object:
    """Alphabetical everywhere, except that a `properties` map puts `type`
    first.

    **Why the exception exists**, measured 2026-08-09 (docs/v1/plan/
    06-model-seam-and-build.md -> "Open defect"): OpenAI's strict structured
    outputs emits an object's keys in the order the schema declares them. Sorted
    alphabetically, `type` — the discriminator of the `BlockProps` union — came
    *last* in every variant, after `text`, `label`, `emphasis` and the rest. So
    the model wrote a block's content before declaring what kind of block it
    was, and a discriminator that arrives last cannot discriminate anything: the
    choice has already been made.

    The measured effect was not subtle. 12 of 13 text blocks came back as
    `eyebrow` — the union's first member — carrying a median of ~100 and up to
    210 characters against a 24-character cap, because when the text was written
    nothing had yet committed to a block type. Three other interventions were
    tried first and none of them moved it, for the same reason: a prompt
    describing what an eyebrow is, per-variant schema `description`s, and
    reordering the union all speak to a decision the model makes *after* the
    prose is already on the page.

    Determinism is preserved, which is what this function is actually for: the
    ordering is total and content-independent, so the cached prefix stays stable
    (docs/v1/ai-pipeline.md -> prompt caching). It changes once, on the commit
    that introduces it.
    """
    if isinstance(node, dict):
        return {k: _ordered(node[k]) for k in _key_order(node, sorted(node))}
    if isinstance(node, list):
        return [_ordered(v) for v in node]
    return node


def _key_order(node: dict[str, object], keys: list[str]) -> list[str]:
    """`type` first inside a `properties` map, alphabetical everywhere else."""
    parent_is_properties = "type" in keys and _looks_like_properties(node)
    if not parent_is_properties:
        return keys
    return ["type", *(k for k in keys if k != "type")]


def _looks_like_properties(node: dict[str, object]) -> bool:
    """A `properties` map's values are all schemas — objects. A schema node's
    own `type` is a string (`"object"`, `"string"`), so the two are told apart
    by what `type` maps to, not by tracking the path down from the root."""
    value = node.get("type")
    return isinstance(value, dict)
