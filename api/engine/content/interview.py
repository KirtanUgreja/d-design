"""The interview: at most five questions, each with three suggested answers,
always skippable (docs/v4/content.md -> Interview).

One call writes the questions. Code drops what the brief already answers and
maps answers back onto the brief; the interview never gates the deck.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from engine.content.arcs import arc_for
from engine.llm.openrouter import ModelError, Seam
from engine.models import Answer, Brief, Pasted
from lib.result import Err, Result, ok

PROMPT_VERSION = "interview.v1"
MAX_QUESTIONS = 5
NO_PROOF = ("none yet", "search the web")

Fills = Literal["audience", "ask", "thought", "proof", "length", "extra"]

SYSTEM = """You prepare a short interview before a presentation is written. The speaker is a
founder or salesperson presenting to win something. Ask at most five questions, in this order,
each with exactly three suggested answers written for THIS brief:

1. audience — who is in the room, and what do they already believe?
2. ask — what should they do at the end (the amount, the decision, the next meeting)?
3. thought — the one sentence they must remember. Suggestions are candidate theses.
4. proof — what proof do you have (traction, revenue, customers, pilots, quotes)? Suggestions
   are exactly "None yet", "Search the web", and one naming the kind of proof this speaker
   likely has; picking that one asks them to paste it.
5. length — how many minutes, and presenting live or sending it?

Skip a question the brief already answers, and use the freed place for one deck-type question
(fills "extra"): an investor update asks for the period and KPIs; sales asks for the buyer's
words for their pain; a launch asks for the availability date. Never ask about brand colours.
Suggestions are short (at most 15 words) and never invent a specific number."""


class Question(BaseModel):
    fills: Fills
    question: str
    suggestions: list[str] = Field(min_length=3, max_length=3)


class Questions(BaseModel):
    questions: list[Question]


def _answered(q: Question, brief: Brief) -> bool:
    return (q.fills == "audience" and bool(brief.audience)) or (
        q.fills == "ask" and bool(brief.ask)
    )


async def questions(seam: Seam, brief: Brief, *, model: str) -> Result[list[Question], ModelError]:
    result = await seam.complete_json(
        "interview",
        Questions,
        system=SYSTEM,
        user=(
            f"Deck type: {arc_for(brief.deck_type)}\nAudience: {brief.audience or 'not stated'}\n"
            f"The ask: {brief.ask or 'not stated'}\nBrief: {brief.prompt}"
        ),
        model=model,
        prompt_version=PROMPT_VERSION,
        max_tokens=6000,  # reasoning comes out of it too
    )
    if isinstance(result, Err):
        return result
    kept = [q for q in result.value.questions if not _answered(q, brief)]
    return ok(kept[:MAX_QUESTIONS])


def apply(brief: Brief, answered: list[tuple[Question, str]]) -> Brief:
    """Fold answers into the brief. A skipped question is simply absent."""
    update: dict[str, object] = {}
    answers = list(brief.answers)
    pasted = list(brief.pasted)
    for q, text in answered:
        text = text.strip()
        if not text:
            continue
        answers.append(Answer(qid=q.fills, question=q.question, text=text))
        if q.fills == "audience":
            update["audience"] = text
        elif q.fills == "ask":
            update["ask"] = text
        elif q.fills == "proof" and text.lower() not in NO_PROOF:
            pasted.append(Pasted(title="Proof, from the interview", text=text))
        elif q.fills == "length":
            minutes = re.search(r"\d+", text)
            if minutes:
                update["minutes"] = int(minutes.group(0))
            if re.search(r"\bsend|email|read\b", text, re.I):
                update["delivery"] = "send"
    return brief.model_copy(update={**update, "answers": answers, "pasted": pasted})
