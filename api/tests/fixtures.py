"""A golden deck fixture: schema-valid, no presentational values, and it
exercises the block types the literary grammar allows (text, quote, image).
This is the fixture the round-trip test (Pydantic and generated Zod agree) and
the codegen no-diff check both rely on.

The family is editorial-serif (literary grammar): legal roles are headline,
body, quote, media, aside; legal spans are full, two-thirds, half. Every slide
layout here is a legal move in that grammar, and the opener leads with a
full-width region. Stat and chart blocks are exercised in the slide-builder
and renderer tests under a family whose grammar allows them.
"""

from __future__ import annotations

from typing import Literal

from schema.deck import (
    Cta,
    Deck,
    ImageBlock,
    LayoutRegion,
    LayoutStructure,
    QuoteBlock,
    Slide,
    TextBlock,
)

Role = Literal["headline", "body", "media", "stats", "quote", "chart", "aside"]


def _layout(*roles: Role) -> LayoutStructure:
    """A full-span layout from a list of roles — legal in the literary grammar."""
    return LayoutStructure(regions=[LayoutRegion(role=role, span="full") for role in roles])


def golden_deck() -> Deck:
    return Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id="s1",
                title="The quiet power of editorial design",
                layout=LayoutStructure(
                    regions=[
                        LayoutRegion(role="headline", span="full", emphasis="primary"),
                        LayoutRegion(role="body", span="full"),
                    ]
                ),
                blocks=[
                    TextBlock(
                        kind="text", style="headline", content="The quiet power of editorial design"
                    ),
                    TextBlock(
                        kind="text",
                        style="body",
                        content="How restraint, typography, and rhythm make a brand unforgettable.",
                    ),
                ],
                cta=Cta(label="Read the essay", destination="https://example.com/essay"),
                motion_intent="reveal",
            ),
            Slide(
                id="s2",
                title="Three ways to be remembered",
                layout=LayoutStructure(
                    regions=[
                        LayoutRegion(role="headline", span="full"),
                        LayoutRegion(role="body", span="full"),
                        LayoutRegion(role="quote", span="full"),
                    ]
                ),
                blocks=[
                    TextBlock(kind="text", style="headline", content="Three ways to be remembered"),
                    TextBlock(
                        kind="text",
                        style="body",
                        content="Restraint, typography, and rhythm each leave a mark.",
                    ),
                    QuoteBlock(
                        kind="quote",
                        text="Design is not just how it looks — it is how it works.",
                        attribution="Steve Jobs",
                    ),
                ],
                motion_intent="reveal",
            ),
            Slide(
                id="s3",
                title="What the reader takes away",
                layout=_layout("headline", "quote"),
                blocks=[
                    TextBlock(kind="text", style="headline", content="What the reader takes away"),
                    QuoteBlock(
                        kind="quote",
                        text="A single idea, held up by evidence, is what survives.",
                        attribution="The author",
                    ),
                ],
                motion_intent="emphasize",
            ),
            Slide(
                id="s4",
                title="Where the effort goes",
                layout=_layout("headline", "media"),
                blocks=[
                    TextBlock(kind="text", style="headline", content="Where the effort goes"),
                    ImageBlock(
                        kind="image",
                        subject="An editorial spread with generous margins and a pull quote",
                        role="illustration",
                        alt="A printed editorial spread with generous margins",
                    ),
                ],
                motion_intent="transition",
            ),
            Slide(
                id="s5",
                title="The shape of the argument",
                layout=LayoutStructure(
                    regions=[
                        LayoutRegion(role="headline", span="full"),
                        LayoutRegion(role="body", span="half"),
                        LayoutRegion(role="aside", span="half"),
                    ]
                ),
                blocks=[
                    TextBlock(kind="text", style="headline", content="The shape of the argument"),
                    TextBlock(
                        kind="text",
                        style="body",
                        content="One claim, held up by evidence, in a clear order.",
                    ),
                    TextBlock(
                        kind="text",
                        style="caption",
                        content="Figure 1 — the argument as a shape.",
                    ),
                ],
                motion_intent="none",
            ),
        ],
    )


GOLDEN_DECK_JSON: dict[str, object] = {
    "family_id": "editorial-serif",
    "slides": [
        {
            "id": "s1",
            "title": "The quiet power of editorial design",
            "layout": {
                "regions": [
                    {"role": "headline", "span": "full", "emphasis": "primary"},
                    {"role": "body", "span": "full"},
                ]
            },
            "blocks": [
                {
                    "kind": "text",
                    "style": "headline",
                    "content": "The quiet power of editorial design",
                },
                {
                    "kind": "text",
                    "style": "body",
                    "content": "How restraint, typography, and rhythm make a brand unforgettable.",
                },
            ],
            "cta": {"label": "Read the essay", "destination": "https://example.com/essay"},
            "motion_intent": "reveal",
        },
        {
            "id": "s2",
            "title": "Three ways to be remembered",
            "layout": {
                "regions": [
                    {"role": "headline", "span": "full"},
                    {"role": "body", "span": "full"},
                    {"role": "quote", "span": "full"},
                ]
            },
            "blocks": [
                {
                    "kind": "text",
                    "style": "headline",
                    "content": "Three ways to be remembered",
                },
                {
                    "kind": "text",
                    "style": "body",
                    "content": "Restraint, typography, and rhythm each leave a mark.",
                },
                {
                    "kind": "quote",
                    "text": "Design is not just how it looks — it is how it works.",
                    "attribution": "Steve Jobs",
                },
            ],
            "motion_intent": "reveal",
        },
        {
            "id": "s3",
            "title": "What the reader takes away",
            "layout": {
                "regions": [
                    {"role": "headline", "span": "full"},
                    {"role": "quote", "span": "full"},
                ]
            },
            "blocks": [
                {"kind": "text", "style": "headline", "content": "What the reader takes away"},
                {
                    "kind": "quote",
                    "text": "A single idea, held up by evidence, is what survives.",
                    "attribution": "The author",
                },
            ],
            "motion_intent": "emphasize",
        },
        {
            "id": "s4",
            "title": "Where the effort goes",
            "layout": {
                "regions": [
                    {"role": "headline", "span": "full"},
                    {"role": "media", "span": "full"},
                ]
            },
            "blocks": [
                {"kind": "text", "style": "headline", "content": "Where the effort goes"},
                {
                    "kind": "image",
                    "subject": "An editorial spread with generous margins and a pull quote",
                    "role": "illustration",
                    "alt": "A printed editorial spread with generous margins",
                },
            ],
            "motion_intent": "transition",
        },
        {
            "id": "s5",
            "title": "The shape of the argument",
            "layout": {
                "regions": [
                    {"role": "headline", "span": "full"},
                    {"role": "body", "span": "half"},
                    {"role": "aside", "span": "half"},
                ]
            },
            "blocks": [
                {"kind": "text", "style": "headline", "content": "The shape of the argument"},
                {
                    "kind": "text",
                    "style": "body",
                    "content": "One claim, held up by evidence, in a clear order.",
                },
                {
                    "kind": "text",
                    "style": "caption",
                    "content": "Figure 1 — the argument as a shape.",
                },
            ],
            "motion_intent": "none",
        },
    ],
}
