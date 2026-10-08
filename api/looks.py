"""A deck's look, shared by the API and the worker: which visual language it
has, its theme, and how often each language and reference has been used
(docs/v4/plan/39-design-reset.md -> Make, 1-3). Pure Python, no browser and
no model, so the API may call it too.
"""

from __future__ import annotations

from collections import Counter

from engine import Deck, build_theme, look_for, recolour
from engine.design.theme import Theme
from store.files import Store


def usage(store: Store) -> tuple[Counter[str], Counter[str]]:
    """How many decks drew each visual language, and how many slides used each
    reference: the sampler and the reference pick take the least used.
    ponytail: reads every deck; a counter table when decks reach thousands."""
    decks = store.all()
    languages = Counter(d.language for d in decks if d.language)
    references = Counter(s.reference for d in decks for s in d.slides if s.reference)
    return languages, references


def with_language(store: Store, deck: Deck, *, exclude: frozenset[str] = frozenset()) -> Deck:
    """The deck's visual language, drawn once (balanced by usage) and kept, so
    every later look of this deck is the same however usage moves. ``exclude``
    is for Another style: never the language just shown."""
    if deck.language and not exclude:
        return deck
    languages, _ = usage(store)
    look = look_for(
        deck.id,
        deck_type=deck.brief.deck_type,
        tone=deck.brief.tone,
        words=deck.brief.prompt,
        nonce=deck.look_nonce,
        usage=languages,
        exclude=exclude,
    )
    return store.update(deck.id, language=look.language)


def theme_of(deck: Deck) -> Theme:
    """The deck's one generated look, recoloured if the user asked for that."""
    look = look_for(
        deck.id,
        deck_type=deck.brief.deck_type,
        tone=deck.brief.tone,
        words=deck.brief.prompt,
        nonce=deck.look_nonce,
        language=deck.language,
    )
    if deck.palette_nonce:
        look = recolour(look, deck.palette_nonce, tone=deck.brief.tone)
    return build_theme(look)
