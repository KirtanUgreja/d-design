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
    <root>/users/<sub>.json             an account (phase 29, local runs)

Every write is atomic (write a temp file, then rename) under a per-deck lock;
a deck write carries the version it read and is refused if another write
landed first. A job is claimed by renaming it from queued/ to running/: the
rename succeeds for exactly one worker. ponytail: one host (flock and rename
are local); phase 29 moves claims to Postgres SKIP LOCKED.

``store/sql.py`` implements the same interface on Postgres; ``store/tenant.py``
scopes either one to a user. The types every store returns live here.
"""

from __future__ import annotations

import fcntl
import json
import os
import secrets
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from engine import Brief, Composed, Deck, Kept, LedgerEntry, Question
from lib.result import Ok, Result, err, ok

if TYPE_CHECKING:
    from store.tenant import Tenant

JobKind = Literal["interview", "outline", "build", "edit"]
UNDO_STEPS = 20  # "Undo restores any of the last 20 operations exactly" (phase 28)
STALE_S = 60.0  # a running job whose heartbeat is older is claimed again


class NoDeckError(FileNotFoundError):
    """No such deck, or not the caller's (store/tenant.py): both look the same.
    A FileNotFoundError, which is what the file store raised before."""


class Job(BaseModel):
    id: str
    kind: JobKind
    deck_id: str
    created: float
    attempts: int = 0
    payload: str = ""  # an edit job's operation, as JSON (worker.py parses it)
    user_id: str | None = None  # the deck's owner when it was enqueued


AvatarOption = str | int | float | bool | list[str]


class Avatar(BaseModel):
    """A DiceBear avatar, drawn in the browser; the web picks the real style."""

    style: str = "notionists"
    seed: str
    options: dict[str, AvatarOption] = {}


class User(BaseModel):
    id: str  # Better Auth's JWT `sub`
    email: str
    name: str
    avatar: Avatar
    created: datetime


def new_avatar() -> Avatar:
    return Avatar(seed=secrets.token_hex(8))


def as_utc(at: datetime) -> datetime:
    """Naive UTC: an aware time is converted, a naive one is taken as UTC."""
    return at.astimezone(UTC).replace(tzinfo=None) if at.tzinfo else at


def since_midnight_utc() -> datetime:
    """The start of today in UTC, naive (how the stores keep times)."""
    return as_utc(datetime.now(UTC)).replace(hour=0, minute=0, second=0, microsecond=0)


def content_type(name: str) -> str:
    suffix = name.rsplit(".", 1)[-1].lower()
    return {
        "html": "text/html; charset=utf-8",
        "pdf": "application/pdf",
        "png": "image/png",
        "json": "application/json",
    }.get(suffix, "application/octet-stream")


def safe_name(name: str) -> bool:
    """An export or upload name: one plain file name, never a path."""
    return bool(name) and "/" not in name and "\\" not in name and not name.startswith(".")


class _Kept(BaseModel):
    html: str
    css: str
    origin: str


class _Questions(BaseModel):
    questions: list[Question]


class History(BaseModel):
    labels: list[str] = []  # one per snapshot, oldest first
    at: int = -1  # the snapshot the deck is at now


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

    def create(self, brief: Brief, owner_id: str | None = None) -> Deck:
        deck_id = secrets.token_hex(6)
        deck = Deck(
            id=deck_id,
            title=brief.prompt[:80],
            brief=brief.model_copy(update={"id": deck_id}),
            owner_id=owner_id,
        )
        _write(self.dir(deck_id) / "deck.json", deck.model_dump_json())
        return deck

    def exists(self, deck_id: str) -> bool:
        return deck_id.isalnum() and (self.dir(deck_id) / "deck.json").exists()

    def read(self, deck_id: str) -> Deck:
        path = self.dir(deck_id) / "deck.json"
        if not path.exists():
            raise NoDeckError(deck_id)
        return Deck.model_validate_json(path.read_text())

    def owner(self, deck_id: str) -> str | None:
        """The deck's owner; None when it has none or does not exist."""
        return self.read(deck_id).owner_id if self.exists(deck_id) else None

    def tenant(self, user_id: str) -> Tenant:
        """This store as ``user_id`` sees it: the only way routes reach decks."""
        from store.tenant import Tenant  # the one wrapper imports both stores

        return Tenant(self, user_id)

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

    def all(self, owner_id: str | None = None) -> list[Deck]:
        """Newest first; only ``owner_id``'s decks when one is given."""
        out = []
        for path in sorted((self.root / "decks").glob("*/deck.json"), key=os.path.getmtime):
            deck = Deck.model_validate_json(path.read_text())
            if owner_id is None or deck.owner_id == owner_id:
                out.append(deck)
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

    def ledger(self, deck_id: str) -> list[LedgerEntry]:
        path = self.dir(deck_id) / "ledger.jsonl"
        if not path.exists():
            return []
        lines = path.read_text().splitlines()
        return [LedgerEntry.model_validate_json(line) for line in lines if line.strip()]

    def daily_spend(self, user_id: str) -> float:
        """The user's model spend since UTC midnight, over the decks they own.
        ponytail: scans every deck; the SQL store sums one indexed column."""
        start = since_midnight_utc()
        return sum(
            e.cost_usd
            for deck in self.all(owner_id=user_id)
            for e in self.ledger(deck.id)
            if as_utc(e.at) >= start
        )

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

    def drop_kept(self, deck_id: str, slide_id: str) -> None:
        """A deleted slide: its finished HTML and its screenshot go."""
        if slide_id.isalnum():
            for suffix in (".json", ".png"):
                (self.slides_dir(deck_id) / f"{slide_id}{suffix}").unlink(missing_ok=True)

    def slide_png(self, deck_id: str, slide_id: str) -> bytes | None:
        if not (deck_id.isalnum() and slide_id.isalnum()):
            return None
        path = self.dir(deck_id) / "slides" / f"{slide_id}.png"
        return path.read_bytes() if path.is_file() else None

    def export(self, deck_id: str, name: str) -> bytes | None:
        """``export-present.html``, ``export-send.html``, ``export.pdf``, ..."""
        if not (deck_id.isalnum() and safe_name(name)):
            return None
        path = self.dir(deck_id) / name
        return path.read_bytes() if path.is_file() else None

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

    # versions: labelled snapshots per operation (phase 28) -----------------

    def _files(self, deck_id: str) -> list[Path]:
        """What a snapshot holds: the deck, its finished slides and their
        screenshots, and the exports, so a restore is exact without a rebuild."""
        d = self.dir(deck_id)
        out = [d / "deck.json"]
        out += sorted((d / "slides").glob("*.json")) + sorted((d / "slides").glob("*.png"))
        out += [d / "export-present.html", d / "export-send.html", d / "export.pdf"]
        return [p for p in out if p.exists()]

    def history(self, deck_id: str) -> History:
        path = self.dir(deck_id) / "versions" / "index.json"
        return History.model_validate_json(path.read_text()) if path.exists() else History()

    def snapshot(self, deck_id: str, label: str) -> History:
        """Record the deck as it is now, as the newest version. A snapshot after
        an undo drops the versions that were ahead of it, like any editor."""
        with self._lock(deck_id):
            h = self.history(deck_id)
            labels = [*h.labels[: h.at + 1], label]
            root = self.dir(deck_id) / "versions"
            n = len(labels) - 1
            for stale in range(n, len(h.labels)):
                shutil.rmtree(root / str(stale), ignore_errors=True)
            for src in self._files(deck_id):
                dst = root / str(n) / src.relative_to(self.dir(deck_id))
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            if len(labels) > UNDO_STEPS + 1:  # the last 20 operations and their base
                shutil.rmtree(root / "0", ignore_errors=True)
                for k in range(1, len(labels)):
                    os.replace(root / str(k), root / str(k - 1))
                labels = labels[1:]
            out = History(labels=labels, at=len(labels) - 1)
            _write(root / "index.json", out.model_dump_json())
            return out

    def restore(self, deck_id: str, to: int) -> Result[History, str]:
        """Put the deck back exactly as snapshot ``to`` left it."""
        with self._lock(deck_id):
            h = self.history(deck_id)
            if not 0 <= to < len(h.labels):
                return err("Nothing more to undo." if to < 0 else "Nothing more to redo.")
            source = self.dir(deck_id) / "versions" / str(to)
            current = self.read(deck_id).version
            for stale in self._files(deck_id):
                if stale.name != "deck.json":
                    stale.unlink()
            for src in source.rglob("*"):
                if src.is_file():
                    dst = self.dir(deck_id) / src.relative_to(source)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            # The restored deck moves forward in version, so a stale write still fails.
            deck = self.read(deck_id).model_copy(update={"version": current + 1})
            _write(self.dir(deck_id) / "deck.json", deck.model_dump_json())
            out = h.model_copy(update={"at": to})
            _write(self.dir(deck_id) / "versions" / "index.json", out.model_dump_json())
            return ok(out)

    # jobs ------------------------------------------------------------------

    def _jobs(self, state: str) -> list[Job]:
        out = []
        for path in (self.root / "jobs" / state).glob("*.json"):
            try:
                out.append(Job.model_validate_json(path.read_text()))
            except FileNotFoundError:
                continue  # claimed between the listing and the read
        return sorted(out, key=lambda j: j.created)

    def busy(self, deck_id: str) -> bool:
        return any(j.deck_id == deck_id for s in ("queued", "running") for j in self._jobs(s))

    def enqueue(self, kind: JobKind, deck_id: str, payload: str = "") -> Job:
        """At most one waiting or running job per deck and kind: a double click
        on Start enqueues one job. Edits are each their own job, done in order."""
        with self._lock(deck_id):
            for state in ("queued", "running"):
                for job in self._jobs(state):
                    if job.deck_id == deck_id and job.kind == kind and kind != "edit":
                        return job
            job = Job(
                id=f"{time.time_ns()}{secrets.token_hex(3)}",
                kind=kind,
                deck_id=deck_id,
                created=time.time(),
                payload=payload,
                user_id=self.owner(deck_id),
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

    # users (phase 29; local runs keep them as files) ---------------------------

    def _user_path(self, sub: str) -> Path:
        if not sub or not all(c.isalnum() or c in "-_" for c in sub):
            raise ValueError("bad user id")
        return self.root / "users" / f"{sub}.json"

    def upsert_user(self, sub: str, email: str, name: str) -> User:
        """The user's row, made on first sight with a random avatar. Later calls
        refresh the email only: the name is the user's to change."""
        found = self.get_user(sub)
        if found is not None and found.email == email:
            return found
        if found is not None:
            found = found.model_copy(update={"email": email})
        else:
            found = User(
                id=sub, email=email, name=name, avatar=new_avatar(), created=datetime.now(UTC)
            )
        _write(self._user_path(sub), found.model_dump_json())
        return found

    def get_user(self, sub: str) -> User | None:
        path = self._user_path(sub)
        return User.model_validate_json(path.read_text()) if path.exists() else None

    def update_user(
        self, sub: str, *, name: str | None = None, avatar: Avatar | None = None
    ) -> User | None:
        """None when there is no such user."""
        found = self.get_user(sub)
        if found is None:
            return None
        if name is not None:
            found = found.model_copy(update={"name": name})
        if avatar is not None:
            found = found.model_copy(update={"avatar": avatar})
        _write(self._user_path(sub), found.model_dump_json())
        return found

    def delete_user(self, sub: str) -> None:
        """The account, every deck it owns, and those decks' jobs and files."""
        path = self._user_path(sub)
        mine = {deck.id for deck in self.all(owner_id=sub)}
        for state in ("queued", "running", "done"):
            for job in self._jobs(state):
                if job.deck_id in mine:
                    folder = self.root / "jobs" / state
                    (folder / f"{job.id}.json").unlink(missing_ok=True)
                    (folder / f"{job.id}.beat").unlink(missing_ok=True)
        for deck_id in mine:
            shutil.rmtree(self.dir(deck_id), ignore_errors=True)
        path.unlink(missing_ok=True)
