"""Layer 1: parse and sanitize model-written HTML (docs/v4/engine.md ->
"Security of AI-written HTML").

An allowlist, not a blocklist. nh3 is the sanitizer; this module owns only the
lists and the limits. There is no ``<a>``, no ``style`` attribute, no ``id``,
no handler, no ``src``: slides contain text in fields and our own components.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import nh3

from engine.design.axes import TEXTURE_KINDS as _AXES_TEXTURES
from engine.design.patterns import SHAPES
from lib.result import Result, err, ok

SVG_TAGS = (
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
)
SVG_GEOMETRY = frozenset(
    {
        "viewbox",
        "viewBox",
        "preserveaspectratio",
        "preserveAspectRatio",
        "d",
        "x",
        "y",
        "width",
        "height",
        "rx",
        "ry",
        "cx",
        "cy",
        "r",
        "x1",
        "y1",
        "x2",
        "y2",
        "points",
        "transform",
    }
)
TAGS = frozenset(
    [
        "div",
        "section",
        "header",
        "footer",
        "h1",
        "h2",
        "h3",
        "p",
        "span",
        "strong",
        "em",
        "small",
        "sup",
        "sub",
        "br",
        "hr",
        "ul",
        "ol",
        "li",
        "blockquote",
        "figure",
        "figcaption",
        "dd-texture",
        "dd-shape",
        "dd-chart",
        "dd-image",
        "dd-visual",
        # Flat SVG the designer draws (studio, 2026-10-09): geometry only, colour
        # through CSS classes the lint holds to theme tokens; no text, no links.
        *SVG_TAGS,
    ]
)
_GLOBAL = frozenset(
    {"class", "data-field", "data-deco", "data-layer", "data-bleed", "data-build", "aria-hidden"}
)
ATTRIBUTES: dict[str, set[str]] = {
    "*": set(_GLOBAL),
    **{tag: set(SVG_GEOMETRY) for tag in SVG_TAGS},
    "dd-texture": {"kind", "tone"},
    "dd-shape": {"kind", "tone"},
    "dd-image": {"aspect"},
}
# An image slot's crop (phase 39); our code fills it after sanitizing.
IMAGE_ASPECTS = frozenset({"3:2", "2:3", "1:1", "16:9", "4:5"})
TEXTURE_KINDS = _AXES_TEXTURES
TEXTURE_TONES = frozenset({"accent", "ink", "surface"})

MAX_ELEMENTS = 240  # a drawing has more elements than a layout
MAX_DEPTH = 12
MAX_BYTES = 28_000

_CLASS = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
_VOID = frozenset({"br", "hr"})


class _Shape(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0
        self.depth = 0
        self.deepest = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.count += 1
        if tag not in _VOID:
            self.depth += 1
            self.deepest = max(self.deepest, self.depth)

    def handle_endtag(self, tag: str) -> None:
        if tag not in _VOID:
            self.depth = max(0, self.depth - 1)


def sanitize(html: str, field_names: frozenset[str]) -> Result[str, str]:
    """Return the cleaned fragment, or why it is refused."""
    if len(html.encode()) > MAX_BYTES:
        return err(f"the html is over {MAX_BYTES} bytes")

    def keep(tag: str, attr: str, value: str) -> str | None:
        if attr == "class":
            names = [n for n in value.split() if _CLASS.match(n)]
            return " ".join(names) or None
        if attr == "data-field":
            return value if value in field_names else None
        if tag == "dd-shape" and attr == "kind":
            return value if value in SHAPES else "disc"
        if tag == "dd-shape" and attr == "tone":
            return value if value in ("accent", "ink", "surface", "rule") else "accent"
        if tag == "dd-image" and attr == "aspect":
            return value if value in IMAGE_ASPECTS else "3:2"
        if tag == "dd-texture" and attr == "kind":
            return value if value in TEXTURE_KINDS else "solid"
        if tag == "dd-texture" and attr == "tone":
            return value if value in TEXTURE_TONES else "accent"
        return value

    clean = nh3.clean(
        html,
        tags=set(TAGS),
        attributes=ATTRIBUTES,
        attribute_filter=keep,
        strip_comments=True,
        link_rel=None,
    )
    shape = _Shape()
    shape.feed(clean)
    if shape.count > MAX_ELEMENTS:
        return err(f"{shape.count} elements; the limit is {MAX_ELEMENTS}")
    if shape.deepest > MAX_DEPTH:
        return err(f"nesting depth {shape.deepest}; the limit is {MAX_DEPTH}")
    if 'class="s"' not in clean.split(">", 1)[0] + ">":
        return err('the fragment must be one <section class="s"> root')
    return ok(clean)
