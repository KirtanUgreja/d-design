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
_NUMBER = re.compile(
    r"(?<![A-Za-z])[$€£]?\d(?:[\d,]*\d)?(?:\.\d+)?"
    r"\s?(?:%|x|\u00d7|thousand\b|million\b|billion\b|bn\b|[kmb]\b)?",
    re.I,
)
_SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}
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


_NAME_BEFORE = re.compile(r"[^\s.!?:;]\s+[A-Z][A-Za-z]+\s$")


_NAMED = re.compile(r"[^\s.!?:;]\s+([A-Z][A-Za-z]+)\s(\d+)\b")
_WORD_BEFORE = re.compile(r"([A-Z][A-Za-z]+)\s$")


def known_names(text: str) -> frozenset[str]:
    """Product names with a number, learned from the brief ("Tessel 2"), so the
    same name reads as a name at the start of a headline too."""
    return frozenset(f"{w} {n}" for w, n in _NAMED.findall(text))


def numbers(text: str, *, names: bool = False, known: frozenset[str] = frozenset()) -> list[str]:
    """The numbers in a piece of copy. A bare year is a date, not a statistic,
    and a bare integer after a capitalised word mid-sentence is part of a name
    ("Tessel 2", "Windows 11"). ponytail: numbers written as words ("nine in
    ten") are not seen; the upgrade is a word-number parser."""
    out = []
    for m in _NUMBER.finditer(text):
        token = m.group(0).strip()
        if _YEAR.match(token):
            continue
        if not names and token.isdigit():
            before = text[: m.start()]
            word = _WORD_BEFORE.search(before)
            if _NAME_BEFORE.search(before) or (word and f"{word.group(1)} {token}" in known):
                continue
        out.append(token)
    return out


def value(token: str) -> float | None:
    """What a number token is worth: "$4.2M", "$4,200,000" and "4.2 million" are equal."""
    m = re.match(r"[$€£]?([\d,]*\d(?:\.\d+)?)\s?([a-z%\u00d7]*)", token.lower())
    if not m:
        return None
    return float(m.group(1).replace(",", "")) * _SCALE.get(m.group(2), 1.0)


def quoted(number: str, passage: str) -> bool:
    """No quote, no fact: the passage states the same number, in any notation."""
    want = value(number)
    # A source passage is searched for every number, names included.
    return want is not None and any(value(n) == want for n in numbers(passage, names=True))


def sourced(number: str, facts: Iterable[Fact]) -> bool:
    """A number is sourced when a live fact states it. Rejected facts count for nothing."""
    return any(
        f.status != "rejected" and (quoted(number, f.text) or (f.value and quoted(number, f.value)))
        for f in facts
    )


def check(
    storyline: Storyline, facts: list[Fact], known: frozenset[str] = frozenset()
) -> list[Issue]:
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
                for n in numbers(text, known=known)
                if not sourced(n, linked)
            ]
    return issues
