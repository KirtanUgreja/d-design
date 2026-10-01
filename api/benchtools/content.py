"""Phase 24 on the bench and at the CLI: the outline gate, the content
metrics, the inverse-spec eval and the injection eval (docs/v4/content.md ->
Evals). The product's own gate arrives with the app in phase 27; this is the
same gate on a terminal.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from engine import Brief, Fact, Seam, Storyline, interview, notes, research, rules, storyline
from engine.models import Citation
from lib.result import Err

Ask = Callable[[str], str]  # input(), injected so tests and --auto never block


# --- the outline, printed -----------------------------------------------------


def show(story: Storyline, facts: list[Fact]) -> str:
    by = {f.id: f for f in facts}
    lines = [f"\nTHESIS  {story.governing_thought}\n"]
    for s in story.slides:
        lines.append(f"{s.id}  {s.beat}  [{s.intent}]")
        for f in s.fields:
            chip = s.provenance.get(f.name, "  ")
            flags = [x for i in f.fact_ids for x in (by[i].flags if i in by else [])]
            proposed = [i for i in f.fact_ids if i in by and by[i].status == "proposed"]
            mark = "  << NUMBER TO APPROVE" if proposed else ""
            more = f"  ({'; '.join(flags)})" if flags else ""
            lines.append(f"    {chip:3} {f.name:11} {f.text}{mark}{more}")
        if s.notes:
            lines.append(f"        notes: {s.notes}")
    cited = [f for f in facts if f.source == "cited"]
    if cited:
        lines.append("\nSOURCES")
        lines += [f"  [{f.id}] {f.value}  {f.citation.url if f.citation else ''}" for f in cited]
    return "\n".join(lines)


# --- the gate -----------------------------------------------------------------


Answered = list[tuple[interview.Question, str]]


def run_interview(questions: list[interview.Question], ask: Ask) -> Answered:
    """One question at a time: a number picks a suggestion, text is an answer,
    Enter skips it, "s" skips the rest."""
    answered: Answered = []
    for q in questions:
        print(f"\n{q.question}")
        for n, s in enumerate(q.suggestions, start=1):
            print(f"  {n}. {s}")
        reply = ask("  answer (1-3, your own words, Enter to skip, s to skip all): ").strip()
        if reply.lower() == "s":
            break
        if reply in ("1", "2", "3"):
            reply = q.suggestions[int(reply) - 1]
        answered.append((q, reply))
    return answered


def gate(facts: list[Fact], ask: Ask) -> bool:
    """Every proposed number is approved or rejected, then the outline is
    approved or not. Approving with a proposed number is not possible."""
    for f in facts:
        if f.status == "proposed":
            reply = ask(
                f"\n  {f.value!r} in “{f.text}” has no source. Approve as illustrative? [a/r] "
            )
            f.status = "approved" if reply.strip().lower() == "a" else "rejected"
    if any(f.status == "rejected" and f.source == "illustrative" for f in facts):
        # ponytail: a rejected number ends the run; the app patches the outline
        # by conversation instead (phase 27).
        print("\nA number was rejected. Add its source to the brief, or run again.")
        return False
    return ask("\nApprove this outline? [y/N] ").strip().lower() == "y"


# --- one outline --------------------------------------------------------------


@dataclass
class Made:
    story: Storyline
    facts: list[Fact]
    row: dict[str, object]


async def make(seam: Seam, brief: Brief, *, model: str, year: int, ask: Ask | None) -> Made | str:
    """Research, storyline, the gate (unless ``ask`` is None), notes."""
    if ask is not None:
        qs = await interview.questions(seam, brief, model=model)
        if not isinstance(qs, Err):
            brief = interview.apply(brief, run_interview(qs.value, ask))
    found = await research.research(seam, brief, model=model, year=year)
    if isinstance(found, Err):
        return f"research failed: {found.error.kind} {found.error.detail[:200]}"
    research_usd = seam.spent_usd
    written = await storyline.write(seam, brief, found.value, model=model)
    if isinstance(written, Err):
        return f"storyline failed: {written.error.kind} {written.error.detail[:200]}"
    w = written.value
    if ask is not None:
        print(show(w.story, w.facts))
        if not gate(w.facts, ask):
            return "not approved"
    with_notes = await notes.write(seam, w.story, model=model)
    story = w.story if isinstance(with_notes, Err) else with_notes.value

    def count(issues: list[rules.Issue], kind: str) -> int:
        return sum(i.kind == kind for i in issues)

    unapproved = {f.id for f in w.facts if f.status != "approved"}
    row: dict[str, object] = {
        "brief": brief.id,
        "slides": len(story.slides),
        "topic_labels_before": count(w.before, "topic_label"),
        "topic_labels_after": count(w.after, "topic_label"),
        "banned_after": count(w.after, "banned"),
        "meta_after": count(w.after, "meta"),
        "numbers_without_approved_fact": sum(
            1 for s in story.slides for f in s.fields for i in f.fact_ids if i in unapproved
        ),
        "illustrative": sum(f.source == "illustrative" for f in w.facts),
        "cited": sum(f.source == "cited" for f in w.facts),
        "notes": sum(bool(s.notes) for s in story.slides),
        "research_usd": round(research_usd, 4),
        "cost_usd": round(seam.spent_usd, 4),
    }
    return Made(story, w.facts, row)


def save(out: Path, made: Made) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "storyline": made.story.model_dump(mode="json"),
                "facts": [f.model_dump(mode="json") for f in made.facts],
                "row": made.row,
            },
            indent=2,
        )
    )


def load(path: Path) -> tuple[Storyline, list[Fact]]:
    data = json.loads(path.read_text())
    return (
        Storyline.model_validate(data["storyline"]),
        [Fact.model_validate(f) for f in data["facts"]],
    )


def notes_unsourced(brief: Brief, story: Storyline, facts: list[Fact]) -> int:
    """Numbers in the speaker notes that no live fact states. Notes are spoken,
    not shown, but a presenter who says a number has to be able to back it."""
    live = [f for f in facts if f.status != "rejected"]
    known = storyline.names(brief)
    return sum(
        not rules.sourced(n, live)
        for s in story.slides
        for n in rules.numbers(s.notes, known=known)
    )


def review(paths: list[Path], seed: int = 24) -> str:
    """One page for the owner's two checks: every outline, and 20 random cited
    facts with the link and the exact quote to open and compare."""
    parts = [
        "# Phase 24 review\n",
        "Outlines: approvable with at most 3 edits? Facts: open each "
        "link; is the number in the quote, and the quote on the page?\n",
    ]
    cited: list[Fact] = []
    for path in paths:
        story, facts = load(path)
        parts.append(f"\n## {path.stem}\n\n```{show(story, facts)}\n```")
        cited += [f for f in facts if f.source == "cited"]
    random.Random(seed).shuffle(cited)  # noqa: S311 - a sample, not a secret
    parts.append("\n## Fact spot check (20)\n")
    for n, f in enumerate(cited[:20], start=1):
        quote = f.citation.snippet if f.citation else ""
        url = f.citation.url if f.citation else ""
        parts.append(f"{n}. **{f.value}** — {f.text}\n   - {url}\n   - quote: “{quote}”\n")
    return "\n".join(parts)


# --- the inverse spec ---------------------------------------------------------

INVERSE_VERSION = "inverse.v2"


class Reconstructed(BaseModel):
    audience: str
    ask: str
    key_message: str


class Scored(BaseModel):
    audience: float = Field(ge=0, le=1)
    ask: float = Field(ge=0, le=1)
    key_message: float = Field(ge=0, le=1)


def deck_text(story: Storyline) -> str:
    return "\n\n".join(
        "\n".join(f.text for f in s.fields if f.name != "source") for s in story.slides
    )


async def inverse(
    seam: Seam, brief: Brief, story: Storyline, *, model: str
) -> dict[str, float] | str:
    """A model reads only the slides and says who they are for, what they ask
    and what they argue; a second call scores that against the brief, 0-1."""
    guess = await seam.complete_json(
        "storyline",
        Reconstructed,
        system="You read a presentation's slide text. Say who it is for, what it asks the "
        "audience to do, and its one key message. One sentence each.",
        user=deck_text(story),
        model=model,
        prompt_version=INVERSE_VERSION,
        max_tokens=600,
    )
    if isinstance(guess, Err):
        return f"reconstruct failed: {guess.error.kind}"
    g = guess.value
    score = await seam.complete_json(
        "storyline",
        Scored,
        system="Someone read only a deck's slides and reconstructed its audience, its ask and "
        "its key message. Score each against what the deck's author intended, from 0 (wrong or "
        "missing) to 1 (the same meaning). Judge meaning, not wording. The author's brief "
        "describes the deck rather than stating its thesis: score the key message 1 when it is "
        "the argument this brief and its material call for.",
        user=(
            f"Intended audience: {brief.audience}\nReconstructed: {g.audience}\n\n"
            f"Intended ask: {brief.ask}\nReconstructed: {g.ask}\n\n"
            f"The brief: {brief.prompt}\nIts material: "
            f"{' '.join(p.text for p in brief.pasted)[:1500] or 'none'}\n"
            f"Reconstructed key message: {g.key_message}"
        ),
        model=model,
        prompt_version=INVERSE_VERSION,
        max_tokens=300,
    )
    if isinstance(score, Err):
        return f"score failed: {score.error.kind}"
    s = score.value
    return {
        "audience": s.audience,
        "ask": s.ask,
        "message": s.key_message,
        "mean": round((s.audience + s.ask + s.key_message) / 3, 3),
    }


# --- the injection corpus -----------------------------------------------------


class Case(BaseModel):
    id: str
    family: str
    brief: Brief
    search_results: list[dict[str, str]] = Field(default_factory=list)
    must_not_contain: list[str]


async def injection(seam: Seam, case: Case, *, model: str) -> list[str] | str:
    """Run the content stages on a hostile case; return what leaked, or
    "refused". The web is not searched: a hostile result is handed over as
    research would pass it. A call that fails for any other reason raises the
    verdict "unmeasured", which is a failure (a failure to measure is an error)."""
    brief = case.brief.model_copy(update={"research": False})
    facts = research.user_facts(brief)
    for n, r in enumerate(case.search_results, start=1):
        facts.append(
            Fact(
                id=f"w{n}",
                text=r["content"],
                source="cited",
                status="approved",
                citation=Citation(url=r["url"], title=r["title"], snippet=r["content"]),
            )
        )
    written = await storyline.write(seam, brief, facts, model=model)
    if isinstance(written, Err):
        # A refusal holds the channel; anything else measured nothing.
        return "refused" if written.error.kind == "refused" else "unmeasured"
    story = written.value.story
    text = "\n".join(
        [story.governing_thought, *story.key_points]
        + [f.text for s in story.slides for f in s.fields]
    ).lower()
    return [bad for bad in case.must_not_contain if bad.lower() in text]
