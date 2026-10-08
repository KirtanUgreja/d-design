"""The exemplar library: the product's taste asset (docs/v4/design-engine.md).

An exemplar is a finished composition in the slide contract. It does four
jobs: prompt inspiration, the deterministic fallback when repair fails, style
tiles (phase 23), and a QA fixture — every exemplar must itself pass the lint
and the browser checks under every theme.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from pydantic import BaseModel

from engine.llm.openrouter import parse_fenced
from lib.result import Err

LIBRARY = Path(__file__).resolve().parent.parent.parent / "library" / "exemplars"


class _Meta(BaseModel):
    intent: str
    archetype: str
    idea: str
    fields: dict[str, str]


@dataclass(frozen=True)
class Exemplar:
    id: str
    intent: str
    archetype: str
    idea: str
    fields: dict[str, str]
    html: str
    css: str

    def prompt(self) -> str:
        return (
            f"### {self.id} — archetype: {self.archetype}; made for: {self.intent}\n"
            f"Idea: {self.idea}\n```html\n{self.html}\n```\n```css\n{self.css}\n```"
        )


@cache
def load_all() -> tuple[Exemplar, ...]:
    found: list[Exemplar] = []
    for path in sorted(LIBRARY.glob("*.html")):
        text = path.read_text()
        head, _, _ = text.partition("\n")
        meta = _Meta.model_validate(json.loads(head.removeprefix("<!--").removesuffix("-->")))
        blocks = parse_fenced(text, "html", "css")
        if isinstance(blocks, Err):
            raise ValueError(f"{path.name}: {blocks.error}")  # a broken library is a bug
        found.append(
            Exemplar(
                path.stem,
                meta.intent,
                meta.archetype,
                meta.idea,
                meta.fields,
                blocks.value["html"],
                blocks.value["css"],
            )
        )
    return tuple(found)


ARCHETYPES = ("poster", "split", "stack", "grid", "band", "corner")


def fill(ex: Exemplar, words: dict[str, str], *, keep_deco: bool = True) -> str:
    """The exemplar's html with each data-field's text replaced by ``words``."""
    return fill_html(ex.html, words, keep_deco=keep_deco)


def fill_html(source: str, words: Mapping[str, str], *, keep_deco: bool = True) -> str:
    """``source`` with each data-field's text replaced by ``words``.
    A field with no words is removed, never left holding the sample text: a
    filled slide must not show a word or number the user did not give."""

    def swap(m: re.Match[str]) -> str:
        text = words.get(m.group(3), "")
        return f"{m.group(1)}{html.escape(text)}{m.group(4)}" if text else ""

    out = re.sub(
        r'(<(\w+)\b[^>]*\bdata-field="([\w-]+)"[^>]*>)(?:.*?)(</\2>)', swap, source, flags=re.S
    )
    if not keep_deco:
        out = re.sub(r"<(\w+)\b[^>]*\bdata-deco\b[^>]*>.*?</\1>", "", out, flags=re.S)
    return out


def best_for(plan_fields: set[str], intent: str, archetype: str) -> list[Exemplar]:
    """Exemplars that can hold every one of the slide's fields, best first:
    the same archetype, then the same intent, then the fewest unused fields."""
    fits = [e for e in load_all() if plan_fields <= set(e.fields)]
    return sorted(
        fits,
        key=lambda e: (
            e.archetype != archetype,
            e.intent != intent,
            len(set(e.fields) - plan_fields),
            e.id,
        ),
    )
