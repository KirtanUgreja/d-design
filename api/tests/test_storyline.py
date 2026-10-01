"""Storyline assembly: every number is linked to a fact or becomes a proposed
illustrative one; provenance and source lines are code's job (offline)."""

from __future__ import annotations

from engine.content.storyline import Draft, DraftSlide, assemble
from engine.models import Brief, Citation, Fact

BRIEF = Brief(
    id="b", prompt="Launch Tessel 2, the offline notes app.", ask="Upgrade today", delivery="send"
)
CITED = Fact(
    id="w1",
    text="41% of workers lost a call to a weak signal",
    value="41%",
    source="cited",
    status="approved",
    as_of="2025",
    citation=Citation(url="https://ons.gov.uk/r", title="Survey", publisher="ONS", snippet="41%"),
)
MINE = Fact(
    id="u1", text="Tessel 2 syncs 3 devices without a server.", source="user", status="approved"
)
GONE = Fact(id="w2", text="97% prefer it", value="97%", source="cited", status="rejected")


def _slide(**kw: object) -> DraftSlide:
    base: dict[str, object] = {
        "beat": "proof",
        "intent": "number",
        "kicker": "",
        "headline": "Weak signal costs calls",
        "points": [],
        "stat": "",
        "stat_label": "",
        "fact_ids": [],
    }
    return DraftSlide.model_validate(base | kw)


def test_numbers_link_to_facts_or_become_proposed_illustrations() -> None:
    draft = Draft(
        governing_thought="Offline notes never fail you",
        key_points=["a"],
        slides=[
            _slide(
                headline="Weak signal drops 41% of calls",
                stat="41%",
                stat_label="of workers lost a call",
                fact_ids=["w1"],
            ),
            _slide(headline="Tessel 2 syncs 3 devices directly", fact_ids=[]),
            _slide(headline="97% of teams will switch by spring", fact_ids=["w2"]),
        ],
    )
    story, facts = assemble(draft, BRIEF, [CITED, MINE, GONE])
    s1, s2, s3 = story.slides

    stat = next(f for f in s1.fields if f.name == "stat")
    assert stat.fact_ids == ["w1"] and s1.provenance["stat"] == "WEB"
    assert next(f.text for f in s1.fields if f.name == "source") == "ONS, 2025"
    assert stat.budget_words == 4  # 3 words, x1.5 for a deck that is sent

    head2 = next(f for f in s2.fields if f.name == "headline")
    assert head2.fact_ids == ["u1"] and s2.provenance["headline"] == "YOU"

    # A rejected fact backs nothing: 97% becomes a proposed illustration.
    [illus] = [f for f in facts if f.source == "illustrative"]
    assert (illus.value, illus.status) == ("97%", "proposed")
    assert next(f.text for f in s3.fields if f.name == "source") == "Illustrative"
    assert len(story.key_points) == 3
