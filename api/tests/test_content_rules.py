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
    assert rules.quoted("$50,000", "Nine accounts above $50k ACV")
    assert rules.quoted("$3.9 million", "Revenue was $3.9M")
    assert not rules.quoted("$3.9 billion", "Revenue was $3.9M")
    assert rules.numbers("Up 18% on Q2") == ["18%"]
    assert rules.numbers("Founded in 2019, now $4.2M ARR and 3x growth") == ["$4.2M", "3x"]
    assert rules.numbers("Upgrade to Tessel 2 for 3 devices") == ["3"]
    assert rules.numbers("3 teams moved to Windows 11") == ["3"]
    assert rules.numbers("Launched in May. Drive 200 teams") == ["200"]
    known = rules.known_names("Launch deck for Tessel 2, the offline notes app.")
    assert known == {"Tessel 2"}
    assert rules.numbers("Tessel 2 works offline for 3 devices", known=known) == ["3"]


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


def test_a_proof_suggestion_asks_for_the_proof_itself() -> None:
    from benchtools.content import run_interview
    from engine.content.interview import Question

    q = Question(
        fills="proof",
        question="What proof do you have?",
        suggestions=["None yet", "Search the web", "Beta tester quotes"],
    )
    replies = iter(["3", "“It never lost a note on the Tube.” — beta tester"])
    [(_, text)] = run_interview([q], lambda _: next(replies))
    assert text.startswith("“It never lost")
    replies = iter(["3", ""])
    [(_, text)] = run_interview([q], lambda _: next(replies))
    assert text == ""  # nothing pasted: treated as no proof, not as a description
    replies = iter(["1"])
    [(_, text)] = run_interview([q], lambda _: next(replies))
    assert text == "None yet"


def test_a_picked_proof_placeholder_is_not_proof_and_the_product_is_material() -> None:
    from engine.content.interview import Question, apply
    from engine.models import Brief

    proof = Question(
        fills="proof",
        question="What proof do you have?",
        suggestions=["None yet", "Search the web", "Pilot results to paste"],
    )
    product = Question(fills="product", question="What does Swarvani AI do?", suggestions=[])
    brief = Brief(id="b", prompt="create a launch deck about swarvani ai")
    out = apply(
        brief,
        [(proof, "Pilot results to paste"), (product, "It turns a voice note into a spec.")],
    )
    assert [p.title for p in out.pasted] == ["What it does, from the interview"]
    assert [a.qid for a in out.answers] == ["product"]  # the placeholder is dropped entirely
    pasted = apply(brief, [(proof, "12 pilots, 3 paid")])
    assert [p.text for p in pasted.pasted] == ["12 pilots, 3 paid"]


def test_auto_takes_its_arc_from_the_brief() -> None:
    from engine.content.arcs import arc_for

    assert arc_for("auto", "create a launch deck about swarvani ai") == "launch"
    assert arc_for("auto", "Our Q3 investor update") == "investor_update"
    assert arc_for("auto", "Raise a seed round for Tessel") == "pitch"
    assert arc_for("sales", "launch") == "sales"  # a chosen type always wins
