"""The presentational-value backstop.

The schema has no field that accepts a hex code, a pixel value, a font name or
a duration — that is the structural half of the invariant. This is the runtime
half: a walk over every string in a generated tree, run before the tree is
stored or rendered.

WHEN THIS FIRES, THE SCHEMA HAS A GAP A VALUE SLIPPED THROUGH. Add the missing
concept to the art direction. NEVER add an exception to the check. The check is
allowed to be this strict because there is never a legitimate reason for AI
output to contain these tokens, and the next person to hit a false positive
will be tempted to widen the regex instead — which is how the product's spine
quietly stops being one.

It is a real control rather than belt-and-braces: structured-output enforcement
varies by provider, so a hex code is a generation that fails validation, not
one that was impossible to emit.
"""

import re

from lib.result import Result, err, ok

PRESENTATIONAL = re.compile(
    r"#[0-9a-f]{3,8}\b|[\d.]+(px|rem|em|pt|ms|s)\b|\b(rgb|hsl|cubic-bezier)\(",
    re.IGNORECASE,
)

# Two exemptions, both written as an explicit skip rather than as a loosened
# regex — the file's own rule, applied to itself twice.
#
# Slot code is CSS/HTML/JS by definition — it is presentational the way a
# stylesheet is — and what contains it is the sandbox: `srcdoc` with
# `allow-scripts` and no `allow-same-origin`, no storage, no cookies, no parent
# DOM. `description` is NOT exempt, because that is the field the editor shows
# and an AI edit operates on.
SLOT_CODE_FIELDS = frozenset({"html", "css", "js"})

# `Stat.value` is a short numeric-with-unit string by design — the spec's own
# examples are "10x", "2.4M", and "<50ms" (docs/v1/scene-schema.md). That last
# one is indistinguishable, lexically, from a CSS duration: the regex exists to
# catch "240ms" used as a styling value, and a benchmark number is the same six
# characters. This is not a styling value leaking through — `Stat` has no
# styling field to leak from — it is the regex matching content it was never
# meant to look at. The type is what actually protects the invariant here: a
# `Stat` cannot carry a hex code or a font name no matter what its `value`
# says, because the schema has nowhere for those to go. `label` is NOT exempt;
# only the fields the spec explicitly says may look like a unit.
STAT_CONTENT_FIELDS = frozenset({"value", "prefix", "suffix"})


def _walk(node: object, path: str, hits: list[str]) -> None:
    if isinstance(node, str):
        if PRESENTATIONAL.search(node):
            hits.append(f"{path}: {node[:80]!r}")
        return
    if isinstance(node, dict):
        block_type = node.get("type")
        exempt = (
            SLOT_CODE_FIELDS
            if block_type == "slot"
            else STAT_CONTENT_FIELDS
            if block_type == "stat"
            else frozenset[str]()
        )
        for key, value in node.items():
            if key in exempt:
                continue
            _walk(value, f"{path}.{key}", hits)
        return
    if isinstance(node, list):
        for i, value in enumerate(node):
            _walk(value, f"{path}[{i}]", hits)


def assert_no_presentational_values(tree: object) -> Result[None]:
    hits: list[str] = []
    _walk(tree, "$", hits)
    if hits:
        return err(
            "invalid_input", "presentational values in AI output: " + "; ".join(hits)
        )
    return ok(None)
