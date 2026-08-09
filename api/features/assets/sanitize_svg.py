"""The one place SVG is touched (docs/v1/plan/10-brand-and-uploads.md).

**Sanitization is the second layer, not the first.** An SVG accepted here is
served only through `<img>`, where a script cannot execute even if this file
missed something — and that layering is the actual control. The security spec
is blunt about why: DOMPurify, the best tool available for this, had four
distinct XSS bypasses disclosed in 2025-2026, and "a design that trusted
sanitization alone would have been exploitable four times in eighteen months"
(docs/security/content-and-web.md). Rejecting SVG outright would hurt real
users, because logos are almost always SVG.

**Allowlist, not denylist.** A denylist of dangerous elements is a list of the
attacks someone had already thought of; every one of those four bypasses was a
way of writing something the list did not name. An element or attribute that is
not named below does not survive, so a new SVG feature is inert here until
someone adds it deliberately.

**Two different attacks, two different controls.** The XSS shape (`<script>`,
`onload=`, `href` off-document) is handled by the allowlist. The denial-of-
service shape — billion-laughs entity expansion, pathological nesting — is not
an XSS problem and an allowlist does nothing about it: the expansion happens in
the parser, before any element is inspected. `defusedxml` refuses entity
declarations outright, and depth is capped while walking.
"""

from xml.etree.ElementTree import Element, register_namespace, tostring

# The refusal classes live in `defusedxml.common`; `defusedxml.ElementTree`
# re-exports them at runtime but its type stubs do not, so they are imported
# from where they are actually defined rather than silenced with an ignore.
from defusedxml.common import DTDForbidden, EntitiesForbidden
from defusedxml.ElementTree import ParseError, fromstring

from lib.result import Result, err, ok

_SVG_NS = "http://www.w3.org/2000/svg"

# Emit `<svg …>` rather than `<ns0:svg xmlns:ns0=…>`. Both are the same document
# to a parser, but the prefixed form is the kind of difference that makes a
# designer think the file was mangled — and this output is what they will see if
# they ever download their own logo back.
register_namespace("", _SVG_NS)

# Shape, geometry and grouping. Nothing that loads, scripts, or reaches out of
# the document: no `script`, no `foreignObject` (an HTML escape hatch inside
# SVG), no `image` (a fetch), no `a` (a navigation), no `animate` (which can
# set another element's attributes, including ones removed below).
_ELEMENTS = frozenset(
    {
        "svg",
        "g",
        "defs",
        "title",
        "desc",
        "symbol",
        "use",
        "path",
        "rect",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "text",
        "tspan",
        "linearGradient",
        "radialGradient",
        "stop",
        "clipPath",
        "mask",
        "pattern",
    }
)

# Presentational and geometric attributes only. Every `on*` handler is absent
# by construction rather than by pattern — an allowlist has no `on*` in it —
# and so is every URL-bearing attribute except `href`, which is checked below.
_ATTRIBUTES = frozenset(
    {
        "d",
        "cx",
        "cy",
        "r",
        "rx",
        "ry",
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "width",
        "height",
        "points",
        "transform",
        "viewBox",
        "preserveAspectRatio",
        "fill",
        "fill-opacity",
        "fill-rule",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-dasharray",
        "stroke-opacity",
        "opacity",
        "offset",
        "stop-color",
        "stop-opacity",
        "gradientUnits",
        "gradientTransform",
        "clip-path",
        "clip-rule",
        "mask",
        "id",
        "class",
        "font-family",
        "font-size",
        "font-weight",
        "text-anchor",
        "letter-spacing",
        "xmlns",
    }
)

# `<use href="#local">` is legitimate and is how an icon sprite works.
# `<use href="https://…">` and `xlink:href` to anything off-document are a
# fetch the page did not ask for, which is the SSRF-shaped half of the SVG
# problem rather than the XSS-shaped one.
_HREF = frozenset({"href", "{http://www.w3.org/1999/xlink}href"})

# Deep enough for any real logo, shallow enough that a nesting bomb dies here.
# Distinct from the entity bomb, which `defusedxml` stops in the parser: this is
# the version that arrives as literally nested groups and costs CPU on the walk.
_MAX_DEPTH = 40
_MAX_ELEMENTS = 20_000

# Caps the input before it is handed to a parser at all. A parser that has
# already allocated is a parser you have already lost.
MAX_SVG_BYTES = 2 * 1024 * 1024


def sanitize_svg(raw: bytes) -> Result[bytes]:
    """A safe SVG, or the reason it was refused.

    Each refusal is its own sentence because each is a different question the
    user is owed an answer to — "a rejected upload is a user holding their own
    logo, being told no by a product that has just claimed it will keep them on
    brand" (docs/v1/plan/10-brand-and-uploads.md).
    """
    if len(raw) > MAX_SVG_BYTES:
        return err(
            "invalid_input",
            f"that SVG is larger than {MAX_SVG_BYTES // (1024 * 1024)}MB; "
            "export it without embedded images and try again",
        )

    try:
        root = fromstring(raw.decode("utf-8", errors="strict"))
    except (EntitiesForbidden, DTDForbidden):
        # The billion-laughs family. Refused in the parser, before expansion,
        # which is the only place refusing it costs nothing.
        return err(
            "invalid_input",
            "that SVG declares XML entities, which this reader does not accept; "
            "re-export it from your design tool",
        )
    except (ParseError, UnicodeDecodeError):
        return err("invalid_input", "that file is not readable as SVG")

    if _localname(root.tag) != "svg":
        return err("invalid_input", "that file is not an SVG")

    count = _clean(root, depth=0)
    if isinstance(count, Err_):
        return err("invalid_input", count.message)

    # Re-serialized from the cleaned tree, so what is stored is this parser's
    # own output rather than the user's bytes with pieces cut out. Anything the
    # walk did not understand is gone by construction, including comments,
    # processing instructions and any stray namespace declaration.
    return ok(tostring(root, encoding="utf-8", xml_declaration=True))


class Err_:
    """Internal marker so `_clean` can report a depth/size refusal upward
    without either raising or growing a Result type for a private walk."""

    def __init__(self, message: str) -> None:
        self.message = message


def _clean(node: Element, depth: int, seen: list[int] | None = None) -> int | Err_:
    budget = seen if seen is not None else [0]
    if depth > _MAX_DEPTH:
        return Err_("that SVG is nested too deeply to process safely")
    budget[0] += 1
    if budget[0] > _MAX_ELEMENTS:
        return Err_("that SVG has too many shapes in it to process safely")

    for child in list(node):
        if _localname(child.tag) not in _ELEMENTS:
            node.remove(child)
            continue
        result = _clean(child, depth + 1, budget)
        if isinstance(result, Err_):
            return result

    node.tag = f"{{{_SVG_NS}}}{_localname(node.tag)}"
    for name, value in list(node.attrib.items()):
        if name in _HREF:
            # Local fragment only. Anything else is a fetch.
            if not value.startswith("#"):
                del node.attrib[name]
            continue
        if _localname(name) not in _ATTRIBUTES:
            del node.attrib[name]
            continue
        # `url(...)` in a presentation attribute can point off-document even
        # when the attribute itself is on the allowlist.
        if "url(" in value.lower() and "url(#" not in value.lower().replace(" ", ""):
            del node.attrib[name]

    return budget[0]


def _localname(tag: str) -> str:
    """`{namespace}local` -> `local`. Namespaces are stripped and rewritten to
    the SVG one on the way out, so a foreign-namespace element cannot smuggle a
    name past the allowlist by wearing a different prefix."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""
