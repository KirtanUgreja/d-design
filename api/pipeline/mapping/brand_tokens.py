"""Brand-to-family mapping — facts to semantic roles, contrast enforced.

Extraction is separate from mapping (phase 17). The kit stores *facts* (a
logo's dominant color, registry font ids). Mapping turns those into the
family's *semantic roles* (accent, paper, ink) with contrast enforced,
because a marketer's logo color is never guaranteed to work as text.

The output is a set of token overrides for the family's roles —
presentational values, yes, but these are the family boundary, not the model
output. The model never sees a hex (the no_style backstop stays intact); the
renderer applies these tokens the same way it applies a family's own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEX = re.compile(r"^#([0-9a-fA-F]{6})$")

# The family-neutral paper and ink a fallback keeps text readable against.
_DEFAULT_PAPER = (255, 255, 255)
_DEFAULT_INK = (17, 17, 17)

# WCAG AA for normal text.
AA_TEXT = 4.5


@dataclass(frozen=True)
class BrandFacts:
    """The kit's extracted facts — what extraction produces, before mapping.

    Each is a hex color or None when the kit has none (a logo's dominant
    color, a typed accent, etc.).
    """

    accent_hex: str | None = None
    paper_hex: str | None = None
    ink_hex: str | None = None


@dataclass(frozen=True)
class BrandTokens:
    """The mapped semantic roles for one family. Each value is a 6-digit hex.

    A value is present only when the brand fact could be mapped to it with
    contrast enforced; otherwise the family's own token stands (a fallback,
    never a forced non-compliant value).
    """

    accent: str | None = None
    paper: str | None = None
    ink: str | None = None

    def overrides(self) -> dict[str, str]:
        out: dict[str, str] = {}
        if self.accent is not None:
            out["accent"] = self.accent
        if self.paper is not None:
            out["paper"] = self.paper
        if self.ink is not None:
            out["ink"] = self.ink
        return out


def _parse_hex(value: str) -> tuple[int, int, int] | None:
    m = _HEX.match(value.strip().lower())
    if m is None:
        return None
    h = m.group(1)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _channel(c: int) -> float:
    c8 = c / 255
    return c8 / 12.92 if c8 <= 0.03928 else ((c8 + 0.055) / 1.055) ** 2.4


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """WCAG contrast ratio between two colors (4.5:1 is AA for text)."""
    la = 0.2126 * _channel(a[0]) + 0.7152 * _channel(a[1]) + 0.0722 * _channel(a[2])
    lb = 0.2126 * _channel(b[0]) + 0.7152 * _channel(b[1]) + 0.0722 * _channel(b[2])
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def map_brand_to_family(
    accent_hex: str | None,
    paper_hex: str | None,
    ink_hex: str | None,
    *,
    paper: tuple[int, int, int] = _DEFAULT_PAPER,
    ink: tuple[int, int, int] = _DEFAULT_INK,
) -> BrandTokens:
    """Map the kit's facts to the family's roles with contrast enforced.

    A brand value that cannot reach AA contrast against its pair is NOT
    forced — the family's own token stands. Fail-closed on anything that
    grants: a forced unreadable accent grants nothing but hurts the deck.
    """
    accent, mapped_paper, mapped_ink = None, None, None

    paper_rgb = _parse_hex(paper_hex) if paper_hex else None
    if paper_rgb is not None and contrast_ratio(paper_rgb, ink) >= AA_TEXT:
        mapped_paper = _hex(paper_rgb)

    ink_rgb = _parse_hex(ink_hex) if ink_hex else None
    if ink_rgb is not None and contrast_ratio(ink_rgb, paper) >= AA_TEXT:
        mapped_ink = _hex(ink_rgb)

    accent_rgb = _parse_hex(accent_hex) if accent_hex else None
    if accent_rgb is not None and contrast_ratio(accent_rgb, paper) >= AA_TEXT:
        accent = _hex(accent_rgb)

    return BrandTokens(accent=accent, paper=mapped_paper, ink=mapped_ink)
