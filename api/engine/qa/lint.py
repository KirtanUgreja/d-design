"""Layer 2: lint model-written CSS (docs/v4/design-engine.md -> "Slide lint").

Static, after sanitizing and before rendering. Scoping is the browser's job
(one shadow root per slide); this only reads declarations and refuses. Every
problem is returned, so one repair can fix them all.
"""

from __future__ import annotations

import re

import tinycss2
from tinycss2.ast import Node

MAX_BYTES = 16_000

_COLOR_PROPS = frozenset(
    [
        "color",
        "background-color",
        "border-color",
        "border-top-color",
        "border-right-color",
        "border-bottom-color",
        "border-left-color",
        "outline-color",
        "fill",
        "stroke",
        "text-decoration-color",
        "caret-color",
        "column-rule-color",
    ]
)
# Shorthands that may carry a colour among other values.
_COLOR_SHORTHANDS = frozenset(
    [
        "background",
        "border",
        "border-top",
        "border-right",
        "border-bottom",
        "border-left",
        "outline",
        "text-decoration",
        "column-rule",
    ]
)
_BANNED_PROPS = frozenset(
    [
        "filter",
        "backdrop-filter",
        "text-shadow",
        "mask",
        "mask-image",
        "-webkit-mask",
        "-webkit-mask-image",
        "animation",
        "animation-name",
        "transition",
        "font",
        "opacity",
        # Multi-column text breaks a sentence across columns (team slide, 2026-10-09).
        "columns",
        "column-count",
        "column-width",
    ]
)
_BANNED_FUNCTIONS = frozenset(
    [
        "url",
        "linear-gradient",
        "radial-gradient",
        "conic-gradient",
        "repeating-linear-gradient",
        "repeating-radial-gradient",
        "repeating-conic-gradient",
        "rgb",
        "rgba",
        "hsl",
        "hsla",
        "hwb",
        "lab",
        "lch",
        "oklab",
        "oklch",
        "color",
        "color-mix",
        "image-set",
    ]
)
_NAMED = frozenset(
    [
        "black",
        "white",
        "red",
        "green",
        "blue",
        "yellow",
        "orange",
        "purple",
        "pink",
        "gray",
        "grey",
        "silver",
        "maroon",
        "navy",
        "teal",
        "olive",
        "lime",
        "aqua",
        "fuchsia",
        "brown",
        "beige",
        "ivory",
        "gold",
        "indigo",
        "violet",
        "cyan",
        "magenta",
        "crimson",
        "coral",
        "salmon",
        "khaki",
        "tan",
        "turquoise",
        "lavender",
    ]
)
_OK_COLOR_WORDS = frozenset({"transparent", "currentcolor", "inherit", "none"})
_VAR = re.compile(r"var\(\s*(--[a-z0-9-]+)\s*\)")
# html and body as type selectors only: ".body" is an ordinary class name.
_BAD_SELECTOR = re.compile(r":host|:root|(?<![\w.#-])(?:html|body)(?![\w-])|\\")
_EMOJI = re.compile("[\U0001f000-\U0001faff☀-➿⬀-⯿️]")


def _functions(tokens: list[Node]) -> list[str]:
    found: list[str] = []
    for token in tokens:
        if token.type == "url":
            # tinycss2 reads an unquoted url(...) as its own token, not a function.
            found.append("url")
        elif token.type == "function":
            found.append(token.lower_name)
            found += _functions(token.arguments)
        elif token.type in ("() block", "[] block", "{} block"):
            found += _functions(token.content)
    return found


def _idents(tokens: list[Node]) -> list[str]:
    return [t.lower_value for t in tokens if t.type == "ident"]


def _has_hash(tokens: list[Node]) -> bool:
    return any(t.type == "hash" for t in tokens)


def _units(tokens: list[Node]) -> list[str]:
    found: list[str] = []
    for token in tokens:
        if token.type == "dimension":
            found.append(token.lower_unit)
        elif token.type == "function":
            found += _units(token.arguments)
    return found


def _check(name: str, value: list[Node], raw: str, important: bool) -> list[str]:
    out: list[str] = []
    text = raw.strip().lower()
    variables = _VAR.findall(text)
    functions = _functions(value)

    if important:
        out.append(f"{name}: !important is not allowed")
    if name in _BANNED_PROPS:
        hint = {
            "font": "set font-family, font-size and font-weight separately",
            "opacity": "use --c-ink-2 for quieter text, not opacity",
        }.get(name, "it is not allowed in slide CSS")
        out.append(f"{name}: banned — {hint}")
        return out
    for function in functions:
        if function in _BANNED_FUNCTIONS:
            out.append(f"{name}: {function}() is not allowed; use theme tokens")
    if any(unit in ("vw", "vh", "vmin", "vmax") for unit in _units(value)):
        out.append(f"{name}: viewport units are not allowed; the canvas is 1920x1080px")

    if name in _COLOR_PROPS or name in _COLOR_SHORTHANDS:
        if _has_hash(value):
            out.append(f"{name}: raw colour; use var(--c-…)")
        for word in _idents(value):
            if word in _NAMED:
                out.append(f"{name}: colour keyword '{word}'; use var(--c-…)")
        for variable in variables:
            if name in _COLOR_PROPS and not variable.startswith("--c-"):
                out.append(f"{name}: {variable} is not a colour token")
    if name in _COLOR_PROPS and not variables and not set(_idents(value)) <= _OK_COLOR_WORDS:
        out.append(f"{name}: must be var(--c-…), transparent or currentColor")

    if name == "font-family" and not (len(variables) == 1 and variables[0].startswith("--f-")):
        out.append("font-family: must be exactly var(--f-display), var(--f-text) or var(--f-label)")
    if name == "font-size" and not (len(variables) == 1 and variables[0].startswith("--t-")):
        out.append("font-size: must be exactly one var(--t-…) token")
    if name == "font-weight" and not (len(variables) == 1 and variables[0].startswith("--w-")):
        out.append("font-weight: must be var(--w-display), var(--w-regular) or var(--w-bold)")
    if (
        name.startswith("border")
        and name.endswith("radius")
        and text
        not in (
            "0",
            "0px",
            "50%",
            "var(--radius)",
        )
    ):
        out.append(f"{name}: only 0, 50% or var(--radius)")
    if name == "box-shadow" and text not in ("none", "var(--shadow-hard)"):
        out.append("box-shadow: only var(--shadow-hard)")
    if name == "position" and text in ("fixed", "sticky"):
        out.append(f"position: {text} is not allowed")
    if name == "z-index" and text.lstrip("-").isdigit() and int(text) > 20:
        out.append("z-index: above 20")
    if name == "letter-spacing":
        # Tighter than this and words touch at display sizes ("Lineargives",
        # 2026-10-09); the theme's own --track-display is the tightest it goes.
        for token in value:
            if token.type == "dimension" and token.lower_unit == "em" and token.value < -0.03:
                out.append("letter-spacing: tighter than -0.03em; words touch")
            if token.type == "dimension" and token.lower_unit == "px" and token.value < -3:
                out.append("letter-spacing: tighter than -3px; words touch")
    if name == "content" and any(t.type == "string" and t.value.strip() for t in value):
        out.append("content: text in CSS is not allowed; text lives in data-field nodes")
    return out


def lint(css: str) -> list[str]:
    """Every problem found, as short sentences a model can act on."""
    if len(css.encode()) > MAX_BYTES:
        return [f"the css is over {MAX_BYTES} bytes"]
    problems: list[str] = []
    if _EMOJI.search(css):
        problems.append("emoji in css")
    if "<" in css:
        # "</style>" would end the element and turn the rest into live HTML.
        problems.append("'<' is not allowed in css")
    rules = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
    for rule in rules:
        if rule.type == "error":
            problems.append(f"css parse error: {rule.message}")
        elif rule.type == "at-rule":
            problems.append(f"@{rule.lower_at_keyword}: at-rules are not allowed")
        elif rule.type == "qualified-rule":
            selector = tinycss2.serialize(rule.prelude).strip()
            if _BAD_SELECTOR.search(selector):
                problems.append(f"selector '{selector}': :host, :root, html, body are not allowed")
            for item in tinycss2.parse_blocks_contents(
                rule.content, skip_comments=True, skip_whitespace=True
            ):
                if item.type == "declaration":
                    raw = tinycss2.serialize(item.value)
                    problems += _check(item.lower_name, item.value, raw, item.important)
                elif item.type == "error":
                    problems.append(f"css parse error in '{selector}': {item.message}")
                else:
                    problems.append(f"'{selector}': nested rules are not allowed")
    # One line per distinct problem keeps the repair prompt short.
    return list(dict.fromkeys(problems))
