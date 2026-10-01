"""The content rules (phase 24 -> Verify): the detectors catch every v3 sample
headline, pass the bench's assertion headlines, and trace every number."""

from __future__ import annotations

from benchtools import files
from engine.content import rules
from engine.models import Fact, PlanField, SlidePlan, Storyline

# Every headline of the three v3 sample decks (git show v3-final:samples/).
V3 = [
    "Conclusion and Future Outlook",
    "Introduction to Remote Work Trends",
    "Key Statistics for 2026",
    "Remote Work Growth Stats",
    "Remote Work Satisfaction Rates",
    "State of Remote Work in 2026: The Numbers That Matter",
    "Trends Influencing Remote Work",
    "Visual Data Representation",
    "Introducing Our CRM for Agencies",
    "Challenges Agencies Face",
    "Validation of Demand",
    "Key Features of Our CRM",
    "Our Launch Approach",
    "Visual Elements of Our Product",
    "Typography and Design Philosophy",
    "Get Involved with Our Pilot",
    "Aurora Roasters",
    "Taste the difference",
    "The roast",
    "From bean to cup",
]


def test_every_v3_headline_is_a_topic_label() -> None:
    assert [h for h in V3 if not rules.topic_label(h)] == []


def test_bench_assertion_headlines_pass() -> None:
    flagged = []
    for brief_id in files.brief_ids():
        outline = files.load(brief_id).outline
        assert outline is not None
        for slide in outline.slides:
            headline = next(f.text for f in slide.fields if f.name == "headline")
            if rules.topic_label(headline):
                flagged.append(headline)
    assert flagged == []


def test_banned_meta_and_emoji() -> None:
    assert rules.banned("We leverage AI-powered insights") == ["leverage", "ai-powered"]
    assert rules.banned("It's not just a tool, it's a team") == ["not just X, it's Y"]
    assert rules.banned("Meet Tracewell") == ["Meet <product>"]
    assert rules.banned("Teams meet weekly; the landscaper paid") == []
    assert rules.meta_copy("Prominent statistics will illustrate growth")
    assert rules.meta_copy("This slide shows our traction")
    assert rules.meta_copy("Revenue tripled in a year") is None
    assert rules.emoji("Launch day 🚀")


def test_no_quote_no_fact() -> None:
    passage = "In the beta, teams cut mean time to resolution by 68% across 1,200 incidents."
    assert rules.quoted("68%", passage)
    assert rules.quoted("1200", passage)
    assert not rules.quoted("86%", passage)
    assert rules.numbers("Founded in 2019, now $4.2M ARR and 3x growth") == ["$4.2M", "3x"]
    assert rules.numbers("Upgrade to Tessel 2 for 3 devices") == ["3"]
    assert rules.numbers("3 teams moved to Windows 11") == ["3"]
    assert rules.numbers("Launched in May. Drive 200 teams") == ["200"]


def test_check_flags_unsourced_and_ignores_rejected_facts() -> None:
    fact = Fact(id="f1", text="MTTR fell 68% in the beta", source="cited", status="approved")
    dead = Fact(id="f2", text="97% of engineers prefer it", source="cited", status="rejected")
    slide = SlidePlan(
        id="s01",
        beat="proof",
        intent="number",
        fields=[
            PlanField(
                name="headline",
                text="Teams resolve incidents 68% faster",
                budget_words=12,
                fact_ids=["f1"],
            ),
            PlanField(name="stat", text="97%", budget_words=3, fact_ids=["f2"]),
        ],
    )
    story = Storyline(
        governing_thought="t",
        deck_type="launch",
        audience="a",
        ask="b",
        key_points=["x", "y", "z"],
        slides=[slide],
    )
    issues = rules.check(story, [fact, dead])
    assert [(i.kind, i.field, i.found) for i in issues] == [("unsourced", "stat", "97%")]


def test_bench_outlines_invent_no_numbers() -> None:
    # Every number in a frozen outline is in its brief: the prompt, the ask or
    # the pasted material. This is the check the storyline stage must pass.
    for brief_id in files.brief_ids():
        item = files.load(brief_id)
        brief, outline = item.brief, item.outline
        assert outline is not None
        given = " ".join([brief.prompt, brief.ask, brief.audience] + [p.text for p in brief.pasted])
        facts = [Fact(id="brief", text=given, source="user", status="approved")]
        for slide in outline.slides:
            for f in slide.fields:
                if f.name != "source":
                    assert all(rules.sourced(n, facts) for n in rules.numbers(f.text)), f.text
