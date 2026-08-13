"""A golden deck fixture: schema-valid, no presentational values, and it
exercises every block type and several archetypes. This is the fixture the
round-trip test (Pydantic and generated Zod agree) and the codegen no-diff
check both rely on.
"""

from __future__ import annotations

from schema.deck import ChartBlock, Cta, Deck, ImageBlock, QuoteBlock, Slide, StatBlock, TextBlock


def golden_deck() -> Deck:
    return Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id="s1",
                title="The quiet power of editorial design",
                layout_archetype="opener",
                variant="centered",
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
                title="Three numbers that matter",
                layout_archetype="stats",
                variant="three",
                blocks=[
                    TextBlock(kind="text", style="headline", content="Three numbers that matter"),
                    StatBlock(kind="stat", value="3.4x", label="more remembered"),
                    StatBlock(kind="stat", value="92%", label="recall after a week"),
                    StatBlock(kind="stat", value="1", label="cohesive voice"),
                ],
                motion_intent="reveal",
            ),
            Slide(
                id="s3",
                title="What the reader takes away",
                layout_archetype="quote",
                variant="centered",
                blocks=[
                    TextBlock(kind="text", style="headline", content="What the reader takes away"),
                    QuoteBlock(
                        kind="quote",
                        text="Design is not just how it looks — it is how it works.",
                        attribution="Steve Jobs",
                    ),
                ],
                motion_intent="emphasize",
            ),
            Slide(
                id="s4",
                title="Where the effort goes",
                layout_archetype="image",
                variant="frame",
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
                layout_archetype="statement",
                variant="left",
                blocks=[
                    TextBlock(kind="text", style="headline", content="The shape of the argument"),
                    ChartBlock(
                        kind="chart",
                        chart_type="bar",
                        title="Recall by format",
                        series=[("Editorial", 92.0), ("Template", 41.0), ("Longform", 78.0)],
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
            "layout_archetype": "opener",
            "variant": "centered",
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
            "title": "Three numbers that matter",
            "layout_archetype": "stats",
            "variant": "three",
            "blocks": [
                {"kind": "text", "style": "headline", "content": "Three numbers that matter"},
                {"kind": "stat", "value": "3.4x", "label": "more remembered"},
                {"kind": "stat", "value": "92%", "label": "recall after a week"},
                {"kind": "stat", "value": "1", "label": "cohesive voice"},
            ],
            "motion_intent": "reveal",
        },
        {
            "id": "s3",
            "title": "What the reader takes away",
            "layout_archetype": "quote",
            "variant": "centered",
            "blocks": [
                {"kind": "text", "style": "headline", "content": "What the reader takes away"},
                {
                    "kind": "quote",
                    "text": "Design is not just how it looks — it is how it works.",
                    "attribution": "Steve Jobs",
                },
            ],
            "motion_intent": "emphasize",
        },
        {
            "id": "s4",
            "title": "Where the effort goes",
            "layout_archetype": "image",
            "variant": "frame",
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
            "layout_archetype": "statement",
            "variant": "left",
            "blocks": [
                {"kind": "text", "style": "headline", "content": "The shape of the argument"},
                {
                    "kind": "chart",
                    "chart_type": "bar",
                    "title": "Recall by format",
                    "series": [["Editorial", 92.0], ["Template", 41.0], ["Longform", 78.0]],
                },
            ],
            "motion_intent": "none",
        },
    ],
}
