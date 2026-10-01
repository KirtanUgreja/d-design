"""The rules for words (docs/v4/content.md -> "Content rules" and "Evals").

Pure functions over text. Each detector returns what it found, so the caller
can show the user, regenerate one field, or count it on the bench. The topic
label check is patterns only; the model check the spec pairs with it runs in
the storyline stage, which regenerates a flagged headline.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from engine.models import Fact, Storyline

# LLM house style. The list grows whenever the wall finds a new one.
BANNED = (
    "in today's fast-paced world",
    "delve",
    "unlock",
    "unleash",
    "harness",
    "leverage",
    "leverages",
    "leveraging",
    "leveraged",
    "game-changer",
    "game changer",
    "seamless",
    "seamlessly",
    "robust",
    "cutting-edge",
    "revolutionize",
    "revolutionise",
    "revolutionizing",
    "supercharge",
    "elevate",
    "empower",
    "empowers",
    "empowering",
    "synergy",
    "synergies",
    "tapestry",
    "landscape",
    "ai-powered",
    "imagine a world",
    "let's dive in",
    "in conclusion",
)
_BANNED = [(p, re.compile(rf"(?<![\w-]){re.escape(p)}(?![\w-])", re.I)) for p in BANNED]
_BANNED_SHAPES = (
    ("not just X, it's Y", re.compile(r"\bnot just\b[^.]{1,60}\bit'?s\b", re.I)),
    ("Meet <product>", re.compile(r"^\s*(?i:meet)\s+[A-Z]")),
)

# Openers that make a headline a label, not a claim.
_LABEL_OPENERS = re.compile(
    r"^\s*(introduction|introducing|overview|key\s|conclusion|agenda|about\s+us|summary|"
    r"thank\s+you|questions|q\s*&\s*a|next\s+steps\s*$|from\s+\w+\s+to\s+\w+\s*$)",
    re.I,
)
_SMALL = frozenset(
    {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "our"}
    | {"the", "their", "to", "vs", "with", "your", "its"}
)
_META = re.compile(
    r"\b(this slide|this deck|this presentation|the following slide|here we will|"
    r"we will (show|explore|discuss|look at|cover)|will (illustrate|showcase|highlight)|"
    r"will be (shown|presented|displayed|illustrated)|in this (section|deck|presentation))\b",
    re.I,
)
_EMOJI = re.compile("[\U0001f000-\U0001faff☀-➿⬀-⯿️]")

# A number as it appears in copy: "$4.2M", "68%", "3x", "1,200", "0.6".
_NUMBER = re.compile(r"[$€£]?\d(?:[\d,]*\d)?(?:\.\d+)?\s?(?:%|x|\u00d7|bn|[kmb]n?\b)?", re.I)
_YEAR = re.compile(r"^(19|20)\d\d$")


@dataclass(frozen=True)
class Issue:
    kind: str  # topic_label · banned · meta · emoji · unsourced · case
    slide_id: str
    field: str
    found: str


def topic_label(headline: str) -> str | None:
    """Why a headline reads as a topic label, or None if it is a claim."""
    words = re.findall(r"[A-Za-z][\w'-]*|\d[\d.,%$]*", headline)
    if _LABEL_OPENERS.match(headline):
        return "label opener"
    if len(words) <= 3:
        return "too short to be a claim"
    rest = [w for w in words[1:] if w.lower() not in _SMALL and w[0].isalpha()]
    capped = [w for w in rest if w[0].isupper() and not w.isupper()]
    if rest and len(capped) / len(rest) > 0.6:
        return "Title Case"
    return None


def banned(text: str) -> list[str]:
    found = [phrase for phrase, rx in _BANNED if rx.search(text)]
    return found + [name for name, rx in _BANNED_SHAPES if rx.search(text)]


def meta_copy(text: str) -> str | None:
    m = _META.search(text)
    return m.group(0) if m else None


def emoji(text: str) -> bool:
    return bool(_EMOJI.search(text))


def numbers(text: str) -> list[str]:
    """The numbers in a piece of copy. A bare year is a date, not a statistic."""
    out = []
    for m in _NUMBER.finditer(text):
        token = m.group(0).strip()
        if _YEAR.match(token):
            continue
        out.append(token)
    return out


def _digits(token: str) -> str:
    return re.sub(r"[^\d.]", "", token.replace(",", "")).rstrip(".")


def quoted(number: str, passage: str) -> bool:
    """No quote, no fact: the number's digits appear verbatim in the passage."""
    want = _digits(number)
    return bool(want) and any(_digits(n) == want for n in numbers(passage))


def sourced(number: str, facts: Iterable[Fact]) -> bool:
    """A number is sourced when a live fact states it. Rejected facts count for nothing."""
    return any(
        f.status != "rejected" and (quoted(number, f.text) or (f.value and quoted(number, f.value)))
        for f in facts
    )


def check(storyline: Storyline, facts: list[Fact]) -> list[Issue]:
    """Every content-rule issue in a storyline, field by field."""
    by_id = {f.id: f for f in facts}
    issues: list[Issue] = []
    for slide in storyline.slides:
        for field in slide.fields:
            text = field.text
            if field.name == "headline":
                why = topic_label(text)
                if why:
                    issues.append(Issue("topic_label", slide.id, field.name, why))
            issues += [Issue("banned", slide.id, field.name, p) for p in banned(text)]
            meta = meta_copy(text)
            if meta:
                issues.append(Issue("meta", slide.id, field.name, meta))
            if emoji(text):
                issues.append(Issue("emoji", slide.id, field.name, "emoji"))
            if field.name == "source":
                continue  # a source line names a source; its date is not a claim
            linked = [by_id[i] for i in field.fact_ids if i in by_id]
            issues += [
                Issue("unsourced", slide.id, field.name, n)
                for n in numbers(text)
                if not sourced(n, linked)
            ]
    return issues
