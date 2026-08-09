"""The injection boundary.

**This is the newest attack surface in the product** (docs/security/content-and-web.md
-> "CSS injection via art-direction tokens"), and it enters with v2 because v2 is
the first version where a token value is not written by us. A token becomes a CSS
custom property, and art directions require `style-src 'unsafe-inline'` — so an
unvalidated token is a script-adjacent injection point on a page carrying a
customer's brand.

## Most of this is already impossible, and that is the point

`schema/art_direction.py` types colours as three floats, lengths as a number and
a unit enum, easings as four floats, and font families as a `Literal` of vetted
names. A value like `red; } body { background: url(//evil` has **no
representation** in that model — Pydantic rejects it at the parse, before this
module runs.

So why does this module exist?

**Because "a control that passes because a different control caught it is a
control you have not tested"** (docs/v2/plan/03-ad-linter.md). The types are the
real defence and this is the assertion that they are, run over the same record
from the other direction: walk every string that survived the parse, and prove
none of them carries a payload. When someone widens a field in two years — a
`description` on a token, a family name freed from the registry, an author's
label emitted into a comment — this fires and the types no longer do.

It is also the layer that catches what a type cannot: a `hex` fallback that
disagrees with the components it is supposed to be a serialization of.

**Rejected, never sanitized.** Sanitizing means guessing what the author meant,
and a guess about a value that is about to become CSS on someone else's launch
page is not a guess worth making.
"""

import re
from typing import TYPE_CHECKING

from schema.art_direction import (
    VETTED_FONT_FAMILIES,
    ArtDirectionRecord,
    LintFinding,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

# The literal sequences that must never appear in any string reaching CSS.
# Lower-cased before matching, because `URL(` and `\75 rl(` are the same attack
# with different typing.
#
# Backslash is here as a whole class rather than a sequence: CSS escapes are how
# every one of the others gets past a naive substring check, so a value with a
# backslash in it is rejected without asking what it was escaping.
_FORBIDDEN = (
    "url(",
    "expression(",
    "@import",
    "</style",
    "javascript:",
    "\\",
    # Not in the spec's list, and here because the others are pointless without
    # them: a value that can close a declaration or a rule can start anything.
    "{",
    "}",
    ";",
)

# Control characters, which no legal token value contains and which are the
# other way to smuggle a delimiter past a substring check.
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")

_CHANNEL_MAX = 255.0


def check_grammar(record: ArtDirectionRecord) -> list[LintFinding]:
    """Every string in the record, and the one value that must agree with
    another."""
    findings: list[LintFinding] = []
    findings.extend(_check_strings(record))
    findings.extend(_check_font_families(record))
    findings.extend(_check_hex_round_trips(record))
    return findings


def _check_strings(record: ArtDirectionRecord) -> "Iterator[LintFinding]":
    """Walk the serialized record and refuse anything with a payload in it.

    Serialized rather than walked as a model, deliberately: the wire form is
    what a designer's tool produces and what a future field will appear in
    automatically. A hand-written walk over known attributes only checks the
    fields somebody remembered to add to it.
    """
    payload = record.model_dump(mode="json", by_alias=True)
    for path, value in _strings(payload):
        lowered = value.lower()
        for needle in _FORBIDDEN:
            if needle in lowered:
                yield LintFinding(
                    rule="GRAMMAR_FORBIDDEN_SEQUENCE",
                    path=path,
                    message=(
                        f"contains {needle!r}, which cannot appear in a token value. "
                        "Token values become CSS custom properties on a page that "
                        "allows inline styles, so a value carrying CSS syntax is an "
                        "injection. The value is rejected rather than stripped."
                    ),
                )
                break
        if _CONTROL.search(value):
            yield LintFinding(
                rule="GRAMMAR_CONTROL_CHARACTER",
                path=path,
                message=(
                    "contains a control character. No legal token value does, and "
                    "they are how a delimiter gets past a check that looks for "
                    "delimiters."
                ),
            )


def _check_font_families(record: ArtDirectionRecord) -> "Iterator[LintFinding]":
    """The one free-text token that is not free text.

    A family name is echoed into a stylesheet, which makes it the most
    natural-looking injection point in the whole system — and it is also the one
    most likely to be waved through, because a font name looks like content
    rather than code. The `Literal` in the schema means a name outside the
    registry has no representation; this says so a second time, because a
    widening of that field is exactly the change nobody would think to test.
    """
    for slot, token in (
        ("tokens.font.display", record.tokens.font.display),
        ("tokens.font.text", record.tokens.font.text),
    ):
        if token.value not in VETTED_FONT_FAMILIES:
            yield LintFinding(
                rule="GRAMMAR_UNVETTED_FONT_FAMILY",
                path=slot,
                message=(
                    f"{token.value!r} is not a vetted family. Families are chosen "
                    "from a registry that maps a name to a self-hosted file; a name "
                    "from outside it either resolves to a system fallback — a page "
                    "published in the wrong typeface, reported as a success — or "
                    "reaches the stylesheet as free text."
                ),
            )


def _check_hex_round_trips(record: ArtDirectionRecord) -> "Iterator[LintFinding]":
    """`hex` is the spec's optional fallback and `components` are authoritative.

    Nothing in this codebase reads the fallback — `from-record.ts` and the
    contrast maths both use the components — so a `hex` that disagrees is not a
    rendering bug today. It is worse than that: it is a string in the record
    that no longer means what the record says it means, which is the exact
    condition under which someone later "fixes" the renderer to read it.

    Checking that it re-serializes is what makes "parsed and re-serialized,
    never the original string" true of the stored value rather than only of the
    code path.
    """
    palette = record.tokens.color
    for name in (
        "bg",
        "bg_elevated",
        "ink",
        "ink_muted",
        "ink_faint",
        "accent",
        "accent_soft",
        "veil",
        "hairline",
    ):
        token = getattr(palette, name)
        expected = "#" + "".join(
            f"{round(component * _CHANNEL_MAX):02x}"
            for component in token.value.components
        )
        if token.value.hex is not None and token.value.hex.lower() != expected:
            yield LintFinding(
                rule="GRAMMAR_HEX_DISAGREES_WITH_COMPONENTS",
                path=f"tokens.color.{name}",
                message=(
                    f"the hex fallback says {token.value.hex} and the components say "
                    f"{expected}. The components are authoritative, so the fallback "
                    "is a string in the record that does not mean what the record "
                    "means."
                ),
            )


def _strings(node: object, prefix: str = "") -> "Iterator[tuple[str, str]]":
    """Every string leaf under a serialized record, with its path.

    Keys as well as values: a DTCG group name becomes part of nothing today, but
    an `$extensions` key is reverse-domain notation chosen by whoever wrote the
    file, and a key is a string that arrived from outside.
    """
    if isinstance(node, str):
        yield prefix, node
    elif isinstance(node, dict):
        for key, child in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(key, str):
                yield f"{path} (key)", key
            yield from _strings(child, path)
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from _strings(child, f"{prefix}[{index}]")
