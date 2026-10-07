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


def test_a_chart_survives_only_if_every_value_is_an_approved_fact() -> None:
    from engine.content.storyline import DraftChart

    arr = [
        Fact(id=f"a{n}", text=f"ARR reached ${v}M in {q}", source="user", status="approved")
        for n, (v, q) in enumerate([(0.6, "Q1"), (1.6, "Q3"), (2.3, "Q4")], start=1)
    ]
    good = DraftChart(
        type="column",
        title="ARR",
        unit="$M",
        labels=["Q1", "Q3", "Q4"],
        values=[0.6, 1.6, 2.3],
        fact_ids=["a1"],
    )
    bad = good.model_copy(update={"values": [0.6, 1.6, 3.1]})
    draft = Draft(
        governing_thought="ARR nearly fourfold",
        key_points=["a"],
        slides=[
            _slide(intent="chart", headline="ARR grew fourfold this year", chart=good),
            _slide(
                intent="chart", headline="ARR will keep compounding", points=["a", "b"], chart=bad
            ),
        ],
    )
    story, _ = assemble(draft, BRIEF, arr)
    kept, dropped = story.slides
    assert kept.intent == "chart" and kept.chart is not None
    assert kept.chart.fact_ids == ["a1", "a2", "a3"]
    assert dropped.chart is None and dropped.intent == "points"


def test_a_before_and_after_chart_needs_every_value_sourced() -> None:
    from engine.content.storyline import DraftChart, chart_spec

    facts = {
        f"r{n}": Fact(id=f"r{n}", text=t, source="user", status="approved")
        for n, t in enumerate(
            [
                "Retention was 81% in Q2",
                "Retention reached 88% in Q3",
                "Activation was 44% in Q2",
                "Activation reached 61% in Q3",
            ],
            start=1,
        )
    }
    draft = DraftChart(
        type="bar",
        title="Q2 to Q3",
        unit="%",
        labels=["Retention", "Activation"],
        values=[88, 61],
        before=[81, 44],
        before_name="Q2",
        after_name="Q3",
        highlight="Activation",
        fact_ids=["r1"],
    )
    spec = chart_spec(draft, facts)
    assert spec is not None
    assert [s.name for s in spec.series] == ["Q2", "Q3"] and spec.highlight == "Activation"
    assert sorted(spec.fact_ids) == ["r1", "r2", "r3", "r4"]
    assert chart_spec(draft.model_copy(update={"before": [81, 40]}), facts) is None
