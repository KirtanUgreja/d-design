"""Research verification (phase 24 -> Verify): a number with no quote in its
source is discarded. Offline: the citations are built here."""

from __future__ import annotations

from engine.content.research import Candidate, user_facts, verify
from engine.llm.openrouter import Citation as Found
from engine.models import Brief, Pasted

PAGE = Found(
    url="https://www.ons.gov.uk/report",
    title="Remote work survey",
    content=(
        "Survey of 4,000 adults.\nIn 2025, 41% of workers   lost a call to a weak signal."
        "\n[...]\nA second passage: 12% switched provider."
    ),
)
FARM = Found(url="https://gitnux.org/stats", title="Stats", content="41% of workers lost a call.")


def _c(**kw: str) -> Candidate:
    base = {
        "need": "cost",
        "measure": "share of workers who lost a call",
        "claim": "41% of workers lost a call to a weak signal",
        "number": "41%",
        "url": "https://www.ons.gov.uk/report/",
        "quote": "In 2025, 41% of workers lost a call to a weak signal.",
        "date": "2025",
    }
    return Candidate.model_validate(base | kw)


def test_a_quoted_number_from_a_returned_page_is_kept() -> None:
    [fact] = verify([_c()], (PAGE,), year=2026)
    assert (fact.source, fact.value, fact.status, fact.flags) == ("cited", "41%", "approved", [])
    assert fact.citation is not None and fact.citation.url == PAGE.url


def test_everything_unproven_is_discarded() -> None:
    dropped = [
        _c(url="https://elsewhere.example/page"),  # never returned by the search
        _c(quote="In 2025, 47% of workers lost a call."),  # not in the page
        _c(number="47%"),  # not in the quote
        _c(url=FARM.url, quote="41% of workers lost a call."),  # a statistics farm
    ]
    assert verify(dropped, (PAGE, FARM), year=2026) == []


def test_old_and_conflicting_numbers_are_kept_and_flagged() -> None:
    old = _c(date="2019")
    rival = _c(
        claim="12% of workers switched provider",
        number="12%",
        quote="A second passage: 12% switched provider.",
    )
    other = _c(
        measure="survey size",
        claim="The survey covered 4,000 adults",
        number="4,000",
        quote="Survey of 4,000 adults.",
    )
    a, b, c = verify([old, rival, other], (PAGE,), year=2026)
    assert "older than 3 years" in a.flags
    assert "conflicts with w2" in a.flags and "conflicts with w1" in b.flags
    assert c.flags == []


def test_user_facts_are_the_brief_sentences_with_numbers() -> None:
    brief = Brief(
        id="b",
        prompt="Launch Tessel 2 to 40 pilot teams.",
        ask="Book a demo",
        pasted=[Pasted(title="n", text="We have 3 customers. They love it.\nARR is $1.2M")],
    )
    assert [f.text for f in user_facts(brief)] == [
        "Launch Tessel 2 to 40 pilot teams.",
        "We have 3 customers.",
        "ARR is $1.2M",
    ]
    assert {f.source for f in user_facts(brief)} == {"user"}


def test_what_the_product_is_needs_a_returned_page_that_says_it() -> None:
    from engine.content.research import About, verify_about

    site = Found(
        url="https://swarvani.ai",
        title="Swarvani",
        content="Swarvani turns a spoken idea into a product spec. Used by 40 teams.",
    )
    lines = [
        About(
            claim="Swarvani turns a spoken idea into a spec",
            url="https://swarvani.ai/",
            quote="Swarvani turns a spoken idea into a product spec.",
        ),
        About(claim="Used by 400 teams", url=site.url, quote="Used by 40 teams."),  # wrong number
        About(claim="It writes code", url=site.url, quote="It writes code."),  # not on the page
        About(claim="It is free", url="https://elsewhere.example", quote="free"),  # not returned
    ]
    [fact] = verify_about(lines, (site,))
    assert (fact.id, fact.value, fact.source, fact.status) == ("a1", None, "cited", "approved")
    assert fact.citation is not None and fact.citation.url == site.url
