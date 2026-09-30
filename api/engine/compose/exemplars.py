"""The exemplar library: the product's taste asset (docs/v4/design-engine.md).

An exemplar is a finished composition in the slide contract. It does four
jobs: prompt inspiration, the deterministic fallback when repair fails, style
tiles (phase 23), and a QA fixture — every exemplar must itself pass the lint
and the browser checks under every theme.
"""

from __future__ import annotations

import json
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
