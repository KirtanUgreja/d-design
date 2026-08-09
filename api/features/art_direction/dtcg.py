"""The DTCG primitive layer: token constructors, and the interchange document.

Two jobs, and they are the same job seen from each side.

**Constructors** are what `seed.py` and any future authoring path build tokens
with. They exist so that `#08090b` is parsed into channels exactly once, here,
rather than at every call site — the same reason `parseHex` exists on the
TypeScript side and the same reason nothing downstream ever holds a hex string.

**`to_document` / `from_document`** are the interchange format. The stored
record keeps `tokens` and `extensions` as siblings because that is what the
columns are; a DTCG *file* nests the second under a `$extensions` key at the
document root, in reverse-domain notation, which is what the spec says and what
a designer's tool would look for. Converting between the two is four lines and
it is the whole of what "we speak DTCG" costs.

The round trip is asserted (`api/tests/test_art_direction_seed.py`), because an
interchange format nobody reads back is a claim rather than a format.

**What this deliberately does not do.** There is no import route, no upload
handler, and no leniency: `from_document` runs the same Pydantic parse as
anything else crossing a boundary, so a token file naming a group we do not
have is rejected rather than partly absorbed. User authoring is late v2 at the
earliest (docs/v2/art-direction-system.md -> "User-authored art directions"),
and when it arrives it arrives through here — one parse at entry, then phase
03's linter on the parsed result, same as anything typed into a control panel.
"""

import re

from lib.result import Result, err, ok
from schema.art_direction import (
    EXTENSION_KEY,
    ArtDirectionRecord,
    DtcgColorToken,
    DtcgColorValue,
    DtcgDimensionToken,
    DtcgDimensionValue,
    DtcgFontFamilyToken,
    DtcgFontWeightToken,
    DtcgNumberToken,
)

_HEX = re.compile(r"^#([0-9a-fA-F]{6})$")

# The DTCG `color` type carries channels in 0-1, not 0-255. Kept as a named
# constant because the same divisor has to appear in `from-record.ts` on the
# way back out, and an 8-bit assumption spelled as a bare 255 in two languages
# is exactly the kind of agreement that drifts unnoticed.
_CHANNEL_MAX = 255.0


def srgb(hex_value: str, alpha: float = 1.0) -> DtcgColorToken:
    """A colour token from the hex the v1 constants were authored in.

    `hex` is kept alongside the components as the spec's optional fallback —
    it costs six characters and it is what makes the stored token readable by
    a human diffing a migration. `components` stays authoritative: the linter's
    APCA and WCAG maths wants channels, and phase 03 must never be tempted to
    re-parse the fallback.

    Raises rather than returning a `Result`. Every caller is a constant in this
    repository, and a literal that fails to parse is a bug in the file that
    wrote it, not an expected failure of an external boundary (rule 3). The
    same split `art-direction.ts`'s `hex()` already makes.
    """
    match = _HEX.match(hex_value)
    if match is None:
        raise ValueError(f"not a 6-digit hex colour: {hex_value!r}")
    digits = match.group(1)
    channels = [int(digits[i : i + 2], 16) / _CHANNEL_MAX for i in (0, 2, 4)]
    return DtcgColorToken(
        value=DtcgColorValue(components=channels, alpha=alpha, hex=f"#{digits.lower()}")
    )


def px(value: float) -> DtcgDimensionToken:
    """The only `dimension` constructor, because `px` is the only unit either
    art direction's space scale uses. `rem` is the other unit the spec allows
    and it gets a constructor the first time a scale wants one — an unused
    builder is a decision nobody made."""
    return DtcgDimensionToken(value=DtcgDimensionValue(value=value, unit="px"))


def family(name: str) -> DtcgFontFamilyToken:
    """The family name, not the registry id. `from-record.ts` resolves it back
    through `FONT_REGISTRY` and fails closed on a family that is not there —
    which is the control that keeps a free-text font family, "the most
    natural-looking free-text token in the whole system", out of the CSS."""
    return DtcgFontFamilyToken(value=name)


def weight(value: int) -> DtcgFontWeightToken:
    return DtcgFontWeightToken(value=value)


def number(value: float) -> DtcgNumberToken:
    return DtcgNumberToken(value=value)


def to_document(record: ArtDirectionRecord) -> dict[str, object]:
    """The record as a DTCG token file.

    Identity travels inside `$extensions` rather than at the document root: a
    root-level `id` would be indistinguishable from a token group called `id`,
    and the spec reserves exactly one place for things it has no concept of.
    """
    tokens = record.tokens.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload = record.extensions.model_dump(mode="json", by_alias=True)
    payload["id"] = record.id
    payload["version"] = record.version
    payload["name"] = record.name
    payload["author"] = record.author
    return {**tokens, "$extensions": {EXTENSION_KEY: payload}}


def from_document(document: dict[str, object]) -> Result[ArtDirectionRecord]:
    """A DTCG token file back into a record. One parse, and it either succeeds
    whole or fails — there is no partial absorption of a file we half
    understand."""
    extensions = document.get("$extensions")
    if not isinstance(extensions, dict):
        return err("invalid_input", "token file carries no $extensions block")
    payload = extensions.get(EXTENSION_KEY)
    if not isinstance(payload, dict):
        return err("invalid_input", f"token file carries no {EXTENSION_KEY} extension")

    tokens = {key: value for key, value in document.items() if key != "$extensions"}
    semantic = dict(payload)
    identity = {
        key: semantic.pop(key, None) for key in ("id", "version", "name", "author")
    }

    try:
        return ok(
            ArtDirectionRecord.model_validate(
                {**identity, "tokens": tokens, "extensions": semantic}
            )
        )
    except ValueError as e:
        # The message names paths and codes, never values — a token file is a
        # customer's design, and this string reaches a log.
        return err("invalid_input", f"token file failed validation: {type(e).__name__}")
