"""THE data module: decks, events, slides, exports and jobs, as files
(docs/v4/engine.md -> Layout, Jobs).

    <root>/decks/<id>/deck.json         the Deck, versioned
    <root>/decks/<id>/questions.json    the interview's questions
    <root>/decks/<id>/events.jsonl      every event, each with a seq
    <root>/decks/<id>/ledger.jsonl      every model call (cost, never content)
    <root>/decks/<id>/slides/<sid>.json a finished slide, for resume
    <root>/decks/<id>/slides/<sid>.png  its QA screenshot
    <root>/decks/<id>/export-<flavour>.html, export.pdf
    <root>/decks/<id>/abort             present = the user aborted
    <root>/jobs/{queued,running,done}/<job>.json, running/<job>.beat

Every write is atomic (write a temp file, then rename) under a per-deck lock;
a deck write carries the version it read and is refused if another write
landed first. A job is claimed by renaming it from queued/ to running/: the
rename succeeds for exactly one worker. ponytail: one host (flock and rename
are local); phase 29 moves claims to Postgres SKIP LOCKED.
"""

from __future__ import annotations

import fcntl
import json
import os
import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from engine import Brief, Composed, Deck, Kept, LedgerEntry, Question
from lib.result import Ok, Result, err, ok

JobKind = Literal["interview", "outline", "build"]
STALE_S = 60.0  # a running job whose heartbeat is older is claimed again


class Job(BaseModel):
    id: str
    kind: JobKind
    deck_id: str
    created: float
    attempts: int = 0


class _Kept(BaseModel):
    html: str
    css: str
    origin: str


class _Questions(BaseModel):
    questions: list[Question]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        for state in ("queued", "running", "done"):
            (root / "jobs" / state).mkdir(parents=True, exist_ok=True)
        (root / "decks").mkdir(parents=True, exist_ok=True)

    # decks ---------------------------------------------------------------

    def dir(self, deck_id: str) -> Path:
        if not deck_id.isalnum():  # ids are ours, but a route passes them through
            raise ValueError("bad deck id")
        return self.root / "decks" / deck_id

    @contextmanager
    def _lock(self, deck_id: str) -> Iterator[None]:
        path = self.dir(deck_id) / ".lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def create(self, brief: Brief) -> Deck:
        deck_id = secrets.token_hex(6)
        deck = Deck(
            id=deck_id, title=brief.prompt[:80], brief=brief.model_copy(update={"id": deck_id})
        )
        _write(self.dir(deck_id) / "deck.json", deck.model_dump_json())
        return deck

    def exists(self, deck_id: str) -> bool:
        return deck_id.isalnum() and (self.dir(deck_id) / "deck.json").exists()

    def read(self, deck_id: str) -> Deck:
        return Deck.model_validate_json((self.dir(deck_id) / "deck.json").read_text())

    def write(self, deck: Deck, *, read_version: int) -> Result[Deck, str]:
        """Save if nobody saved since ``read_version``; the version goes up by one."""
        with self._lock(deck.id):
            current = self.read(deck.id)
            if current.version != read_version:
                return err("the deck changed since it was read")
            saved = deck.model_copy(update={"version": read_version + 1})
            _write(self.dir(deck.id) / "deck.json", saved.model_dump_json())
            return ok(saved)

    def update(self, deck_id: str, **changes: object) -> Deck:
        """Read, change, write, retrying a lost race: for the worker's own writes."""
        while True:
            deck = self.read(deck_id)
            saved = self.write(deck.model_copy(update=changes), read_version=deck.version)
            if isinstance(saved, Ok):
                return saved.value
            time.sleep(0.01)

    def all(self) -> list[Deck]:
        out = []
        for path in sorted((self.root / "decks").glob("*/deck.json"), key=os.path.getmtime):
            out.append(Deck.model_validate_json(path.read_text()))
        return out[::-1]

    def save_questions(self, deck_id: str, questions: list[Question]) -> None:
        _write(
            self.dir(deck_id) / "questions.json", _Questions(questions=questions).model_dump_json()
        )

    def questions(self, deck_id: str) -> list[Question]:
        path = self.dir(deck_id) / "questions.json"
        return _Questions.model_validate_json(path.read_text()).questions if path.exists() else []

    # events --------------------------------------------------------------

    def append_event(self, deck_id: str, event: dict[str, object]) -> int:
        """Append under the lock, numbered: seq is the SSE id a reconnect resumes from."""
        with self._lock(deck_id):
            path = self.dir(deck_id) / "events.jsonl"
            seq = sum(1 for _ in path.open()) + 1 if path.exists() else 1
            with path.open("a") as out:
                out.write(json.dumps({"seq": seq, **event}) + "\n")
            return seq

    def events(self, deck_id: str, after: int = 0) -> list[dict[str, object]]:
        path = self.dir(deck_id) / "events.jsonl"
        if not path.exists():
            return []
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        return [r for r in rows if isinstance(r, dict) and int(r.get("seq", 0)) > after]

    def append_ledger(self, deck_id: str, entries: list[LedgerEntry]) -> None:
        with self._lock(deck_id), (self.dir(deck_id) / "ledger.jsonl").open("a") as out:
            for e in entries:
                out.write(e.model_dump_json() + "\n")

    # slides and exports ----------------------------------------------------

    def slides_dir(self, deck_id: str) -> Path:
        path = self.dir(deck_id) / "slides"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_kept(self, deck_id: str, slide_id: str, kept: Kept) -> None:
        row = _Kept(html=kept.composed.html, css=kept.composed.css, origin=kept.origin)
        _write(self.slides_dir(deck_id) / f"{slide_id}.json", row.model_dump_json())

    def kept(self, deck_id: str) -> dict[str, Kept]:
        out = {}
        for path in self.slides_dir(deck_id).glob("*.json"):
            row = _Kept.model_validate_json(path.read_text())
            out[path.stem] = Kept(Composed(row.html, row.css), row.origin)
        return out

    def save_export(self, deck_id: str, name: str, data: str | bytes) -> None:
        path = self.dir(deck_id) / name
        if isinstance(data, bytes):
            tmp = path.with_name(f".{path.name}.tmp")
            tmp.write_bytes(data)
            os.replace(tmp, path)
        else:
            _write(path, data)

    def abort(self, deck_id: str) -> None:
        _write(self.dir(deck_id) / "abort", "")

    def aborted(self, deck_id: str) -> bool:
        return (self.dir(deck_id) / "abort").exists()

    def clear_abort(self, deck_id: str) -> None:
        (self.dir(deck_id) / "abort").unlink(missing_ok=True)

    # jobs ------------------------------------------------------------------

    def _jobs(self, state: str) -> list[Job]:
        out = []
        for path in (self.root / "jobs" / state).glob("*.json"):
            try:
                out.append(Job.model_validate_json(path.read_text()))
            except FileNotFoundError:
                continue  # claimed between the listing and the read
        return sorted(out, key=lambda j: j.created)

    def enqueue(self, kind: JobKind, deck_id: str) -> Job:
        """At most one waiting or running job per deck and kind: a double click
        on Start enqueues one job."""
        with self._lock(deck_id):
            for state in ("queued", "running"):
                for job in self._jobs(state):
                    if job.deck_id == deck_id and job.kind == kind:
                        return job
            job = Job(
                id=f"{time.time_ns()}{secrets.token_hex(3)}",
                kind=kind,
                deck_id=deck_id,
                created=time.time(),
            )
            _write(self.root / "jobs" / "queued" / f"{job.id}.json", job.model_dump_json())
            return job

    def claim(self) -> Job | None:
        """The oldest queued job, moved to running/ by one atomic rename."""
        for job in self._jobs("queued"):
            src = self.root / "jobs" / "queued" / f"{job.id}.json"
            dst = self.root / "jobs" / "running" / f"{job.id}.json"
            try:
                os.rename(src, dst)
            except FileNotFoundError:
                continue  # another worker won it
            claimed = job.model_copy(update={"attempts": job.attempts + 1})
            _write(dst, claimed.model_dump_json())
            self.beat(claimed)
            return claimed
        return None

    def beat(self, job: Job) -> None:
        _write(self.root / "jobs" / "running" / f"{job.id}.beat", str(time.time()))

    def requeue_stale(self, now: float | None = None) -> list[Job]:
        """Running jobs whose worker stopped beating go back to the queue."""
        now = time.time() if now is None else now
        out = []
        for job in self._jobs("running"):
            beat = self.root / "jobs" / "running" / f"{job.id}.beat"
            last = beat.stat().st_mtime if beat.exists() else 0.0
            if now - last > STALE_S:
                try:
                    os.rename(
                        self.root / "jobs" / "running" / f"{job.id}.json",
                        self.root / "jobs" / "queued" / f"{job.id}.json",
                    )
                except FileNotFoundError:
                    continue
                beat.unlink(missing_ok=True)
                out.append(job)
        return out

    def finish(self, job: Job) -> None:
        src = self.root / "jobs" / "running" / f"{job.id}.json"
        if src.exists():
            os.replace(src, self.root / "jobs" / "done" / f"{job.id}.json")
        (self.root / "jobs" / "running" / f"{job.id}.beat").unlink(missing_ok=True)
