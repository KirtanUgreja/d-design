"""The engine's data model (docs/v4/engine.md -> "Data model").

Pydantic owns every shape. The web app's TypeScript view is generated from the
API's OpenAPI document, never written by hand.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DeckType = Literal["pitch", "sales", "launch", "investor_update", "partnership", "auto"]
Delivery = Literal["live", "send"]
Tone = Literal["plain", "confident", "warm", "bold"]
Provenance = Literal["YOU", "AI", "WEB"]
Stage = Literal[
    "interview",
    "research",
    "storyline",
    "notes",
    "direction",  # retired 2026-10-08 (phase 39); kept so old ledgers still parse
    "compose",
    "repair",
    "revise",
    "image",
    "baseline",
    "smoke",
]


class Pasted(BaseModel):
    title: str
    text: str


class Answer(BaseModel):
    qid: str
    question: str
    text: str


class Brand(BaseModel):
    name: str
    colors: list[str] = Field(default_factory=list, max_length=3)


class Brief(BaseModel):
    id: str
    prompt: str
    pasted: list[Pasted] = Field(default_factory=list)
    deck_type: DeckType = "auto"
    answers: list[Answer] = Field(default_factory=list)
    audience: str = ""
    ask: str = ""
    minutes: int | None = None
    slide_count: int = Field(default=10, ge=3, le=25)
    delivery: Delivery = "live"
    tone: Tone = "confident"
    research: bool = True
    brand: Brand | None = None
    locale: str = "en"


class Citation(BaseModel):
    url: str
    title: str
    publisher: str = ""
    date: str = ""
    snippet: str


class Fact(BaseModel):
    id: str
    text: str
    value: str | None = None
    unit: str | None = None
    source: Literal["user", "cited", "illustrative"]
    citation: Citation | None = None
    status: Literal["proposed", "approved", "rejected"] = "proposed"
    as_of: str = ""  # the year the number describes, when the source says
    flags: list[str] = Field(default_factory=list)  # "older than 3 years" · "conflicts with f3"


class PlanField(BaseModel):
    name: str
    text: str
    budget_words: int
    fact_ids: list[str] = Field(default_factory=list)


class ChartPoint(BaseModel):
    label: str
    value: float


class ChartSeries(BaseModel):
    name: str
    points: list[ChartPoint]


class ChartSpec(BaseModel):
    type: Literal[
        "bar",
        "column",
        "line",
        "area",
        "stacked",
        "dumbbell",
        "slope",
        "diverging",
        "waffle",
        "donut",
    ]
    title: str
    unit: str = ""
    series: list[ChartSeries]
    highlight: str | None = None
    fact_ids: list[str] = Field(min_length=1)


class ImageSpec(BaseModel):
    prompt: str
    why: str
    aspect: Literal["3:2", "2:3"] = "3:2"
    role: Literal["hero", "bleed", "inset"] = "hero"


VisualKind = Literal["waveform", "phone", "browser", "chat", "flow"]


class VisualSpec(BaseModel):
    """A picture of the product's world, drawn by code (components/visuals.py)."""

    kind: VisualKind
    lines: list[str] = Field(default_factory=list, max_length=4)  # short, no numbers


class SlidePlan(BaseModel):
    id: str
    beat: str
    intent: str
    archetype: str = ""
    exemplar_ids: list[str] = Field(default_factory=list)
    fields: list[PlanField]
    chart: ChartSpec | None = None
    image: ImageSpec | None = None
    visual: VisualSpec | None = None
    # Set by the planner: the deck's mark on its ends, a texture on about one
    # slide in three, and nothing on the rest (design-engine.md -> rhythm).
    ornament: Literal["none", "texture", "mark"] = "none"
    notes: str = ""
    provenance: dict[str, Provenance] = Field(default_factory=dict)


class Storyline(BaseModel):
    governing_thought: str
    deck_type: DeckType
    audience: str
    ask: str
    key_points: list[str] = Field(min_length=3, max_length=5)
    slides: list[SlidePlan]


class Defect(BaseModel):
    code: str
    field: str | None = None
    selector: str = ""
    measured: float | str
    threshold: float | str


class SlideQA(BaseModel):
    status: Literal["passed", "flagged", "unmeasured"] = "unmeasured"
    errors: list[Defect] = Field(default_factory=list)
    warnings: list[Defect] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    fingerprint: str = ""
    screenshot: str = ""


class Slide(BaseModel):
    id: str
    plan_id: str
    version: int = 1
    html: str
    css: str
    fields: dict[str, str]
    assets: dict[str, str] = Field(default_factory=dict)
    origin: Literal["authored", "repaired", "exemplar", "reference", "fallback", "edited"] = (
        "authored"
    )
    reference: str = ""  # the library reference it was adapted from (phase 39)
    attempts: int = 1
    qa: SlideQA = Field(default_factory=SlideQA)
    cost_usd: float = 0.0


class LedgerEntry(BaseModel):
    """One model call. Ids, sizes, timings and cost — never prompts or content."""

    at: datetime
    deck_id: str = ""
    job_id: str = ""
    stage: Stage
    slide_id: str | None = None
    model: str
    provider: str = ""
    prompt_version: str = ""
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    attempt: int = 1
    ok: bool = True
    error_kind: str | None = None


class Deck(BaseModel):
    id: str
    schema_version: int = 1
    owner_id: str | None = None
    title: str
    # brief -> interview (questions out) -> outline (being written) -> approve
    # (outline ready, waiting for the user) -> building -> ready; or error/aborted.
    status: Literal[
        "brief", "interview", "outline", "approve", "building", "ready", "error", "aborted"
    ] = "brief"
    error: str = ""  # human copy for the UI, never an exception string
    look_nonce: int = 0  # "another look" bumps it
    palette_nonce: int = 0  # "recolour" bumps it: same look, another palette
    language: str = ""  # its visual language (design/languages.py), drawn once and kept
    # The user's logo (phase 38, per deck): where it goes, and why it was refused.
    logo: Literal["none", "cover", "ends", "all"] = "none"
    logo_note: str = ""
    logo_colour: str = ""  # the logo's main colour: offered as the brand colour, never applied
    brief: Brief
    facts: list[Fact] = Field(default_factory=list)
    storyline: Storyline | None = None
    slides: list[Slide] = Field(default_factory=list)
    budget_usd: float = 5.0
    version: int = 1
