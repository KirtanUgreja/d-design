"""THE tenant wrapper (docs/coderules/README.md rule 9; patterns.md rule 4):
the one way a route reaches a user's decks, over either store.

Reach it as ``store.tenant(user_id)`` on either store; both return this one
class, so there is exactly one wrapper.

Another user's deck behaves as a missing one: ``exists`` is False,
``slide_png`` and ``export`` are None, ``history`` is empty, and every other
deck method raises ``NoDeckError`` (the API checks ``exists`` first and answers
404). It fails closed: the owner is checked before every call, and an empty
user id is refused at construction.

ponytail: ownership is checked in Python, one query per call; row-level
security is deferred until a second database client exists (phase 29 doc).
"""

from __future__ import annotations

from pathlib import Path

from engine import Brief, Deck, Kept, LedgerEntry, Question
from lib.result import Result
from settings import Settings
from store.files import History, Job, JobKind, NoDeckError, Store
from store.sql import SqlStore

AnyStore = Store | SqlStore


def open_store(cfg: Settings) -> AnyStore:
    """Postgres when ``APP_DATABASE_URL`` is set, else the file store."""
    if cfg.database_url:
        return SqlStore(cfg.database_url, cfg.data_dir)
    return Store(cfg.data_dir)


class Tenant:
    def __init__(self, store: AnyStore, user_id: str) -> None:
        if not user_id:
            raise ValueError("a tenant needs a user")
        self.store = store
        self.user_id = user_id

    def _mine(self, deck_id: str) -> bool:
        return deck_id.isalnum() and self.store.owner(deck_id) == self.user_id

    def _check(self, deck_id: str) -> None:
        if not self._mine(deck_id):
            raise NoDeckError(deck_id)

    # decks ---------------------------------------------------------------

    def create(self, brief: Brief) -> Deck:
        return self.store.create(brief, owner_id=self.user_id)

    def exists(self, deck_id: str) -> bool:
        return self._mine(deck_id)

    def read(self, deck_id: str) -> Deck:
        self._check(deck_id)
        return self.store.read(deck_id)

    def write(self, deck: Deck, *, read_version: int) -> Result[Deck, str]:
        self._check(deck.id)
        owned = deck.model_copy(update={"owner_id": self.user_id})
        return self.store.write(owned, read_version=read_version)

    def update(self, deck_id: str, **changes: object) -> Deck:
        self._check(deck_id)
        return self.store.update(deck_id, **{**changes, "owner_id": self.user_id})

    def all(self) -> list[Deck]:
        return self.store.all(owner_id=self.user_id)

    def save_questions(self, deck_id: str, questions: list[Question]) -> None:
        self._check(deck_id)
        self.store.save_questions(deck_id, questions)

    def questions(self, deck_id: str) -> list[Question]:
        self._check(deck_id)
        return self.store.questions(deck_id)

    # events, ledger, spend -------------------------------------------------

    def append_event(self, deck_id: str, event: dict[str, object]) -> int:
        self._check(deck_id)
        return self.store.append_event(deck_id, event)

    def events(self, deck_id: str, after: int = 0) -> list[dict[str, object]]:
        self._check(deck_id)
        return self.store.events(deck_id, after)

    def append_ledger(self, deck_id: str, entries: list[LedgerEntry]) -> None:
        self._check(deck_id)
        self.store.append_ledger(deck_id, entries)

    def ledger(self, deck_id: str) -> list[LedgerEntry]:
        self._check(deck_id)
        return self.store.ledger(deck_id)

    def daily_spend(self) -> float:
        """Raises if it cannot measure; the caller refuses then (rule 10)."""
        return self.store.daily_spend(self.user_id)

    # slides and exports ----------------------------------------------------

    def slides_dir(self, deck_id: str) -> Path:
        self._check(deck_id)
        return self.store.slides_dir(deck_id)

    def kept(self, deck_id: str) -> dict[str, Kept]:
        self._check(deck_id)
        return self.store.kept(deck_id)

    def save_kept(self, deck_id: str, slide_id: str, kept: Kept) -> None:
        self._check(deck_id)
        self.store.save_kept(deck_id, slide_id, kept)

    def drop_kept(self, deck_id: str, slide_id: str) -> None:
        self._check(deck_id)
        self.store.drop_kept(deck_id, slide_id)

    def save_export(self, deck_id: str, name: str, data: str | bytes) -> None:
        self._check(deck_id)
        self.store.save_export(deck_id, name, data)

    def slide_png(self, deck_id: str, slide_id: str) -> bytes | None:
        return self.store.slide_png(deck_id, slide_id) if self._mine(deck_id) else None

    def export(self, deck_id: str, name: str) -> bytes | None:
        return self.store.export(deck_id, name) if self._mine(deck_id) else None

    def abort(self, deck_id: str) -> None:
        self._check(deck_id)
        self.store.abort(deck_id)

    def aborted(self, deck_id: str) -> bool:
        self._check(deck_id)
        return self.store.aborted(deck_id)

    def clear_abort(self, deck_id: str) -> None:
        self._check(deck_id)
        self.store.clear_abort(deck_id)

    # versions --------------------------------------------------------------

    def history(self, deck_id: str) -> History:
        return self.store.history(deck_id) if self._mine(deck_id) else History()

    def snapshot(self, deck_id: str, label: str) -> History:
        self._check(deck_id)
        return self.store.snapshot(deck_id, label)

    def restore(self, deck_id: str, to: int) -> Result[History, str]:
        self._check(deck_id)
        return self.store.restore(deck_id, to)

    # jobs ------------------------------------------------------------------

    def busy(self, deck_id: str) -> bool:
        self._check(deck_id)
        return self.store.busy(deck_id)

    def enqueue(self, kind: JobKind, deck_id: str, payload: str = "") -> Job:
        """The job carries the owner (the store reads it from the deck)."""
        self._check(deck_id)
        return self.store.enqueue(kind, deck_id, payload)
