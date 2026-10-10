"""THE data module on Postgres (phase 29): the interface of ``store/files.py``,
backed by SQLAlchemy over the `app` database (tables: ``store/models.py``).

Chosen when ``APP_DATABASE_URL`` is set (``store/tenant.py`` -> open_store);
SQLite serves the offline tests. Routes reach it only through the one tenant
wrapper (``store/tenant.py``); the worker uses it unscoped.

- A deck write carries the version it read: one conditional UPDATE.
- A job is claimed with ``SELECT ... FOR UPDATE SKIP LOCKED`` on Postgres;
  SQLite takes the write lock at BEGIN, so a plain read-then-update is safe.
- Screenshots and exports are blobs keyed by sha256, linked by name to a deck
  and to each version, so a file many versions share is stored once. A blob
  no link points at is deleted where the link is dropped.
- ``slides_dir`` is local scratch for the worker's browser: a PNG there is
  persisted when its slide is kept or the deck is exported.
"""

from __future__ import annotations

import hashlib
import secrets
import shutil
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

import psycopg
from sqlalchemy import (
    Connection,
    Engine,
    create_engine,
    delete,
    event,
    exists,
    func,
    select,
    update,
)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine.interfaces import DBAPIConnection, Dialect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from engine import Brief, Composed, Deck, Kept, LedgerEntry, Question
from lib.result import Ok, Result, err, ok
from store.files import (
    STALE_S,
    UNDO_STEPS,
    Avatar,
    History,
    Job,
    JobKind,
    NoDeckError,
    User,
    _Kept,
    as_utc,
    content_type,
    new_avatar,
    safe_name,
    since_midnight_utc,
)
from store.models import (
    Base,
    BlobRow,
    DeckFileRow,
    DeckRow,
    EventRow,
    JobRow,
    KeptRow,
    LedgerRow,
    QuestionsRow,
    UserRow,
    VersionFileRow,
    VersionRow,
)

if TYPE_CHECKING:
    from store.tenant import Tenant

CONNECT_RETRY_S = 2.0  # Neon's free tier sleeps; the first connect can fail once


def driver_url(url: str) -> str:
    """Any Postgres URL as SQLAlchemy's psycopg 3 URL; others as given."""
    for scheme in ("postgres://", "postgresql://"):
        if url.startswith(scheme):
            return "postgresql+psycopg://" + url[len(scheme) :]
    return url


def direct_url(url: str) -> str:
    """The direct host for migrations and CREATE DATABASE: Neon's pooled host
    is the direct one with ``-pooler`` after its first label."""
    parts = urlsplit(driver_url(url))
    return urlunsplit(parts._replace(netloc=parts.netloc.replace("-pooler.", ".", 1)))


def make_engine(url: str) -> Engine:
    url = driver_url(url)
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"timeout": 30})

        @event.listens_for(engine, "connect")
        def _sqlite(conn: sqlite3.Connection, _: ConnectionPoolEntry) -> None:
            conn.isolation_level = None  # SQLAlchemy's BEGIN below, not pysqlite's
            conn.execute("PRAGMA foreign_keys=ON")

        @event.listens_for(engine, "begin")
        def _write_lock(conn: Connection) -> None:
            conn.exec_driver_sql("BEGIN IMMEDIATE")

        return engine
    # prepare_threshold=None: Neon's pooler runs PgBouncer in transaction mode.
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"prepare_threshold": None, "connect_timeout": 10},
    )

    @event.listens_for(engine, "do_connect")
    def _retry_once(
        dialect: Dialect,
        _: ConnectionPoolEntry,
        cargs: tuple[str, ...],
        cparams: dict[str, object],
    ) -> DBAPIConnection:
        try:
            return dialect.connect(*cargs, **cparams)
        except psycopg.OperationalError:  # a cold start; SQLAlchemy has not wrapped it yet
            time.sleep(CONNECT_RETRY_S)
            return dialect.connect(*cargs, **cparams)

    return engine


def _now() -> datetime:
    return as_utc(datetime.now(UTC))


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SqlStore:
    def __init__(self, url: str, scratch: Path) -> None:
        self.engine = make_engine(url)
        self.postgres = self.engine.dialect.name == "postgresql"
        self._session = sessionmaker(self.engine, expire_on_commit=False)
        self.scratch = scratch

    def create_tables(self) -> None:
        """For SQLite and tests; Postgres is migrated by Alembic."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def _tx(self) -> Iterator[Session]:
        with self._session.begin() as s:
            yield s

    def _locked(self, s: Session, deck_id: str) -> DeckRow:
        """The deck's row, locked until the transaction ends (Postgres)."""
        row = s.execute(
            select(DeckRow).where(DeckRow.id == deck_id).with_for_update()
        ).scalar_one_or_none()
        if row is None:
            raise NoDeckError(deck_id)
        return row

    @staticmethod
    def _deck(row: DeckRow) -> Deck:
        return Deck.model_validate(row.data).model_copy(
            update={"version": row.version, "owner_id": row.user_id}
        )

    # decks ---------------------------------------------------------------

    def create(self, brief: Brief, owner_id: str | None = None) -> Deck:
        deck_id = secrets.token_hex(6)
        deck = Deck(
            id=deck_id,
            title=brief.prompt[:80],
            brief=brief.model_copy(update={"id": deck_id}),
            owner_id=owner_id,
        )
        now = _now()
        with self._tx() as s:
            s.add(
                DeckRow(
                    id=deck_id,
                    user_id=owner_id,
                    data=deck.model_dump(mode="json"),
                    version=deck.version,
                    aborted=False,
                    history_at=-1,
                    created=now,
                    updated=now,
                )
            )
        return deck

    def exists(self, deck_id: str) -> bool:
        if not deck_id.isalnum():
            return False
        with self._tx() as s:
            return s.get(DeckRow, deck_id) is not None

    def owner(self, deck_id: str) -> str | None:
        """The deck's owner; None when it has none or does not exist."""
        with self._tx() as s:
            return s.scalar(select(DeckRow.user_id).where(DeckRow.id == deck_id))

    def tenant(self, user_id: str) -> Tenant:
        """This store as ``user_id`` sees it: the only way routes reach decks."""
        from store.tenant import Tenant  # the one wrapper imports both stores

        return Tenant(self, user_id)

    def read(self, deck_id: str) -> Deck:
        with self._tx() as s:
            row = s.get(DeckRow, deck_id)
            if row is None:
                raise NoDeckError(deck_id)
            return self._deck(row)

    def write(self, deck: Deck, *, read_version: int) -> Result[Deck, str]:
        """Save if nobody saved since ``read_version``; the version goes up by one."""
        saved = deck.model_copy(update={"version": read_version + 1})
        with self._tx() as s:
            done = s.execute(
                update(DeckRow)
                .where(DeckRow.id == deck.id, DeckRow.version == read_version)
                .values(data=saved.model_dump(mode="json"), version=saved.version, updated=_now())
                .returning(DeckRow.user_id)
                .execution_options(synchronize_session=False)
            ).first()
            if done is not None:
                return ok(saved.model_copy(update={"owner_id": done[0]}))
            if s.get(DeckRow, deck.id) is None:
                raise NoDeckError(deck.id)
        return err("the deck changed since it was read")

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
        query = select(DeckRow).order_by(DeckRow.updated.desc())
        if owner_id is not None:
            query = query.where(DeckRow.user_id == owner_id)
        with self._tx() as s:
            return [self._deck(row) for row in s.scalars(query)]

    def save_questions(self, deck_id: str, questions: list[Question]) -> None:
        data = [q.model_dump(mode="json") for q in questions]
        with self._tx() as s:
            self._locked(s, deck_id)
            s.merge(QuestionsRow(deck_id=deck_id, data=data))

    def questions(self, deck_id: str) -> list[Question]:
        with self._tx() as s:
            row = s.get(QuestionsRow, deck_id)
            return [Question.model_validate(q) for q in row.data] if row else []

    # events and the ledger -------------------------------------------------

    def append_event(self, deck_id: str, event: dict[str, object]) -> int:
        """Numbered under the deck's lock: seq is the SSE id a reconnect resumes from."""
        with self._tx() as s:
            self._locked(s, deck_id)
            last = s.scalar(select(func.max(EventRow.seq)).where(EventRow.deck_id == deck_id))
            seq = (last or 0) + 1
            s.add(EventRow(deck_id=deck_id, seq=seq, data=event))
            return seq

    def events(self, deck_id: str, after: int = 0) -> list[dict[str, object]]:
        query = (
            select(EventRow)
            .where(EventRow.deck_id == deck_id, EventRow.seq > after)
            .order_by(EventRow.seq)
        )
        with self._tx() as s:
            return [{"seq": row.seq, **row.data} for row in s.scalars(query)]

    def append_ledger(self, deck_id: str, entries: list[LedgerEntry]) -> None:
        """Every row carries the deck owner's user_id."""
        with self._tx() as s:
            owner = self._locked(s, deck_id).user_id
            for e in entries:
                s.add(
                    LedgerRow(
                        user_id=owner,
                        deck_id=deck_id,
                        at=as_utc(e.at),
                        cost_usd=e.cost_usd,
                        data=e.model_dump(mode="json"),
                    )
                )

    def ledger(self, deck_id: str) -> list[LedgerEntry]:
        query = select(LedgerRow.data).where(LedgerRow.deck_id == deck_id).order_by(LedgerRow.id)
        with self._tx() as s:
            return [LedgerEntry.model_validate(data) for data in s.scalars(query)]

    def daily_spend(self, user_id: str) -> float:
        """The user's model spend since UTC midnight, over every deck, even deleted ones."""
        query = select(func.coalesce(func.sum(LedgerRow.cost_usd), 0.0)).where(
            LedgerRow.user_id == user_id, LedgerRow.at >= since_midnight_utc()
        )
        with self._tx() as s:
            return float(s.scalar(query) or 0.0)

    # blobs -------------------------------------------------------------------

    def _put_blob(self, s: Session, data: bytes, ctype: str) -> str:
        digest = _digest(data)
        values = {"hash": digest, "data": data, "content_type": ctype, "size": len(data)}
        if self.postgres:
            s.execute(postgresql.insert(BlobRow).values(values).on_conflict_do_nothing())
        else:
            s.execute(sqlite.insert(BlobRow).values(values).on_conflict_do_nothing())
        return digest

    def _link(self, s: Session, deck_id: str, name: str, digest: str) -> None:
        row = s.get(DeckFileRow, (deck_id, name))
        if row is None:
            s.add(DeckFileRow(deck_id=deck_id, name=name, hash=digest))
            s.flush()
            return
        old, row.hash = row.hash, digest
        s.flush()
        if old != digest:
            self._sweep(s, {old})

    def _sweep(self, s: Session, hashes: set[str]) -> None:
        """Delete the blobs among ``hashes`` that nothing links any more."""
        if not hashes:
            return
        s.flush()
        s.execute(
            delete(BlobRow)
            .where(
                BlobRow.hash.in_(hashes),
                ~exists().where(DeckFileRow.hash == BlobRow.hash),
                ~exists().where(VersionFileRow.hash == BlobRow.hash),
            )
            .execution_options(synchronize_session=False)
        )

    def _file(self, deck_id: str, name: str) -> bytes | None:
        query = (
            select(BlobRow.data)
            .join(DeckFileRow, DeckFileRow.hash == BlobRow.hash)
            .where(DeckFileRow.deck_id == deck_id, DeckFileRow.name == name)
        )
        with self._tx() as s:
            return s.scalar(query)

    # slides and exports ----------------------------------------------------

    def slides_dir(self, deck_id: str) -> Path:
        """Local scratch where the worker's browser writes screenshots."""
        if not deck_id.isalnum():
            raise ValueError("bad deck id")
        path = self.scratch / "decks" / deck_id / "slides"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _keep_png(self, s: Session, deck_id: str, slide_id: str) -> None:
        png = self.slides_dir(deck_id) / f"{slide_id}.png"
        if png.is_file():
            digest = self._put_blob(s, png.read_bytes(), "image/png")
            self._link(s, deck_id, f"slides/{slide_id}.png", digest)

    def save_kept(self, deck_id: str, slide_id: str, kept: Kept) -> None:
        with self._tx() as s:
            self._locked(s, deck_id)
            s.merge(
                KeptRow(
                    deck_id=deck_id,
                    slide_id=slide_id,
                    html=kept.composed.html,
                    css=kept.composed.css,
                    origin=kept.origin,
                )
            )
            self._keep_png(s, deck_id, slide_id)

    def kept(self, deck_id: str) -> dict[str, Kept]:
        with self._tx() as s:
            rows = s.scalars(select(KeptRow).where(KeptRow.deck_id == deck_id))
            return {r.slide_id: Kept(Composed(r.html, r.css), r.origin) for r in rows}

    def drop_kept(self, deck_id: str, slide_id: str) -> None:
        """A deleted slide: its finished HTML and its screenshot go."""
        name = f"slides/{slide_id}.png"
        with self._tx() as s:
            self._locked(s, deck_id)
            s.execute(
                delete(KeptRow).where(KeptRow.deck_id == deck_id, KeptRow.slide_id == slide_id)
            )
            link = s.get(DeckFileRow, (deck_id, name))
            if link is not None:
                old = link.hash
                s.delete(link)
                self._sweep(s, {old})
        (self.slides_dir(deck_id) / f"{slide_id}.png").unlink(missing_ok=True)

    def save_export(self, deck_id: str, name: str, data: str | bytes) -> None:
        """An export, and every kept slide's latest screenshot with it (a resumed
        build measures prebuilt slides again without keeping them again)."""
        if not safe_name(name):
            raise ValueError("bad export name")
        raw = data.encode() if isinstance(data, str) else data
        with self._tx() as s:
            self._locked(s, deck_id)
            self._link(s, deck_id, name, self._put_blob(s, raw, content_type(name)))
            kept = s.scalars(select(KeptRow.slide_id).where(KeptRow.deck_id == deck_id))
            for slide_id in list(kept):
                self._keep_png(s, deck_id, slide_id)

    def slide_png(self, deck_id: str, slide_id: str) -> bytes | None:
        if not (deck_id.isalnum() and slide_id.isalnum()):
            return None
        return self._file(deck_id, f"slides/{slide_id}.png")

    def export(self, deck_id: str, name: str) -> bytes | None:
        """``export-present.html``, ``export-send.html``, ``export.pdf``, ..."""
        if not (deck_id.isalnum() and safe_name(name)):
            return None
        return self._file(deck_id, name)

    def _set_abort(self, deck_id: str, value: bool) -> None:
        with self._tx() as s:
            s.execute(update(DeckRow).where(DeckRow.id == deck_id).values(aborted=value))

    def abort(self, deck_id: str) -> None:
        self._set_abort(deck_id, True)

    def aborted(self, deck_id: str) -> bool:
        with self._tx() as s:
            return bool(s.scalar(select(DeckRow.aborted).where(DeckRow.id == deck_id)))

    def clear_abort(self, deck_id: str) -> None:
        self._set_abort(deck_id, False)

    # versions: labelled snapshots per operation (phase 28) -----------------

    def _versions(self, s: Session, deck_id: str) -> list[VersionRow]:
        query = select(VersionRow).where(VersionRow.deck_id == deck_id).order_by(VersionRow.n)
        return list(s.scalars(query))

    def _drop_versions(self, s: Session, rows: list[VersionRow]) -> None:
        if not rows:
            return
        ids = [r.id for r in rows]
        hashes = set(
            s.scalars(select(VersionFileRow.hash).where(VersionFileRow.version_id.in_(ids)))
        )
        s.execute(delete(VersionFileRow).where(VersionFileRow.version_id.in_(ids)))
        s.execute(delete(VersionRow).where(VersionRow.id.in_(ids)))  # and from the identity map
        self._sweep(s, hashes)

    def history(self, deck_id: str) -> History:
        with self._tx() as s:
            at = s.scalar(select(DeckRow.history_at).where(DeckRow.id == deck_id))
            if at is None:
                return History()
            return History(labels=[v.label for v in self._versions(s, deck_id)], at=at)

    def snapshot(self, deck_id: str, label: str) -> History:
        """Record the deck as it is now, as the newest version. A snapshot after
        an undo drops the versions that were ahead of it, like any editor."""
        with self._tx() as s:
            row = self._locked(s, deck_id)
            versions = self._versions(s, deck_id)
            n = row.history_at + 1
            self._drop_versions(s, [v for v in versions if v.n >= n])
            kept = s.scalars(select(KeptRow).where(KeptRow.deck_id == deck_id))
            version = VersionRow(
                deck_id=deck_id,
                n=n,
                label=label,
                deck=row.data,
                kept={
                    k.slide_id: _Kept(html=k.html, css=k.css, origin=k.origin).model_dump()
                    for k in kept
                },
            )
            s.add(version)
            s.flush()
            files = s.scalars(select(DeckFileRow).where(DeckFileRow.deck_id == deck_id))
            for f in list(files):
                s.add(VersionFileRow(version_id=version.id, name=f.name, hash=f.hash))
            versions = [v for v in versions if v.n < n] + [version]
            if len(versions) > UNDO_STEPS + 1:  # the last 20 operations and their base
                self._drop_versions(s, versions[:1])
                versions = versions[1:]
                s.execute(
                    update(VersionRow)
                    .where(VersionRow.deck_id == deck_id)
                    .values(n=VersionRow.n - 1)
                    .execution_options(synchronize_session=False)
                )
            row.history_at = len(versions) - 1
            return History(labels=[v.label for v in versions], at=row.history_at)

    def restore(self, deck_id: str, to: int) -> Result[History, str]:
        """Put the deck back exactly as snapshot ``to`` left it."""
        with self._tx() as s:
            row = self._locked(s, deck_id)
            versions = self._versions(s, deck_id)
            if not 0 <= to < len(versions):
                return err("Nothing more to undo." if to < 0 else "Nothing more to redo.")
            source = versions[to]
            old = set(s.scalars(select(DeckFileRow.hash).where(DeckFileRow.deck_id == deck_id)))
            s.execute(delete(KeptRow).where(KeptRow.deck_id == deck_id))
            s.execute(delete(DeckFileRow).where(DeckFileRow.deck_id == deck_id))
            for slide_id, raw in source.kept.items():
                k = _Kept.model_validate(raw)
                s.add(
                    KeptRow(
                        deck_id=deck_id, slide_id=slide_id, html=k.html, css=k.css, origin=k.origin
                    )
                )
            for f in s.scalars(
                select(VersionFileRow).where(VersionFileRow.version_id == source.id)
            ).all():
                s.add(DeckFileRow(deck_id=deck_id, name=f.name, hash=f.hash))
            # The restored deck moves forward in version, so a stale write still fails.
            version = row.version + 1
            deck = Deck.model_validate(source.deck).model_copy(update={"version": version})
            row.data, row.version, row.updated = deck.model_dump(mode="json"), version, _now()
            row.history_at = to
            self._sweep(s, old)
            return ok(History(labels=[v.label for v in versions], at=to))

    # jobs ------------------------------------------------------------------

    @staticmethod
    def _job(row: JobRow) -> Job:
        return Job.model_validate(
            {
                "id": row.id,
                "kind": row.kind,
                "deck_id": row.deck_id,
                "created": row.created,
                "attempts": row.attempts,
                "payload": row.payload,
                "user_id": row.user_id,
            }
        )

    def _jobs(self, state: str) -> list[Job]:
        query = select(JobRow).where(JobRow.state == state).order_by(JobRow.created)
        with self._tx() as s:
            return [self._job(r) for r in s.scalars(query)]

    def busy(self, deck_id: str) -> bool:
        query = select(JobRow.id).where(
            JobRow.deck_id == deck_id, JobRow.state.in_(("queued", "running"))
        )
        with self._tx() as s:
            return s.scalar(query.limit(1)) is not None

    def enqueue(self, kind: JobKind, deck_id: str, payload: str = "") -> Job:
        """At most one waiting or running job per deck and kind: a double click
        on Start enqueues one job. Edits are each their own job, done in order."""
        with self._tx() as s:
            owner = self._locked(s, deck_id).user_id
            if kind != "edit":
                same = s.scalars(
                    select(JobRow)
                    .where(
                        JobRow.deck_id == deck_id,
                        JobRow.kind == kind,
                        JobRow.state.in_(("queued", "running")),
                    )
                    .order_by(JobRow.created)
                    .limit(1)
                ).first()
                if same is not None:
                    return self._job(same)
            row = JobRow(
                id=f"{time.time_ns()}{secrets.token_hex(3)}",
                kind=kind,
                deck_id=deck_id,
                user_id=owner,
                state="queued",
                created=time.time(),
                attempts=0,
                payload=payload,
                beat=None,
            )
            s.add(row)
            return self._job(row)

    def claim(self) -> Job | None:
        """The oldest queued job, for exactly one worker: SKIP LOCKED passes over
        a row another worker holds, and the state check catches the rest."""
        with self._tx() as s:
            row = s.scalars(
                select(JobRow)
                .where(JobRow.state == "queued")
                .order_by(JobRow.created)
                .limit(1)
                .with_for_update(skip_locked=True)
            ).first()
            if row is None:
                return None
            won = s.connection().execute(
                update(JobRow)
                .where(JobRow.id == row.id, JobRow.state == "queued")
                .values(state="running", attempts=JobRow.attempts + 1, beat=time.time())
                .execution_options(synchronize_session=False)
            )
            if won.rowcount != 1:
                return None
            s.refresh(row)
            return self._job(row)

    def beat(self, job: Job) -> None:
        with self._tx() as s:
            s.execute(update(JobRow).where(JobRow.id == job.id).values(beat=time.time()))

    def requeue_stale(self, now: float | None = None) -> list[Job]:
        """Running jobs whose worker stopped beating go back to the queue."""
        now = time.time() if now is None else now
        with self._tx() as s:
            stale = list(
                s.scalars(
                    select(JobRow)
                    .where(
                        JobRow.state == "running",
                        (JobRow.beat.is_(None)) | (JobRow.beat < now - STALE_S),
                    )
                    .order_by(JobRow.created)
                    .with_for_update(skip_locked=True)
                )
            )
            out = [self._job(r) for r in stale]
            for r in stale:
                r.state, r.beat = "queued", None
            return out

    def finish(self, job: Job) -> None:
        with self._tx() as s:
            s.execute(
                update(JobRow)
                .where(JobRow.id == job.id, JobRow.state == "running")  # a requeued job stays
                .values(state="done", beat=None)
            )

    # users ---------------------------------------------------------------------

    @staticmethod
    def _user(row: UserRow) -> User:
        return User(
            id=row.id,
            email=row.email,
            name=row.name,
            avatar=Avatar.model_validate(row.avatar),
            created=row.created.replace(tzinfo=UTC),
        )

    def upsert_user(self, sub: str, email: str, name: str) -> User:
        """The user's row, made on first sight with a random avatar. Later calls
        refresh the email only: the name is the user's to change."""
        if not sub:
            raise ValueError("bad user id")
        for _ in range(2):  # two first requests at once: one insert wins
            try:
                with self._tx() as s:
                    row = s.get(UserRow, sub)
                    if row is None:
                        row = UserRow(
                            id=sub,
                            email=email,
                            name=name,
                            avatar=new_avatar().model_dump(),
                            created=_now(),
                        )
                        s.add(row)
                    elif row.email != email:
                        row.email = email
                    s.flush()
                    return self._user(row)
            except IntegrityError:
                continue
        raise RuntimeError("could not create the user")

    def get_user(self, sub: str) -> User | None:
        with self._tx() as s:
            row = s.get(UserRow, sub)
            return self._user(row) if row else None

    def update_user(
        self, sub: str, *, name: str | None = None, avatar: Avatar | None = None
    ) -> User | None:
        """None when there is no such user."""
        with self._tx() as s:
            row = s.get(UserRow, sub, with_for_update=True)
            if row is None:
                return None
            if name is not None:
                row.name = name
            if avatar is not None:
                row.avatar = avatar.model_dump()
            return self._user(row)

    def delete_deck(self, deck_id: str) -> None:
        """One deck and, by cascade, its jobs, events, files and versions; then
        the blobs nothing links any more. Its spend stays on the ledger."""
        with self._tx() as s:
            hashes = set(
                s.scalars(select(DeckFileRow.hash).where(DeckFileRow.deck_id == deck_id))
            ) | set(
                s.scalars(
                    select(VersionFileRow.hash)
                    .join(VersionRow, VersionRow.id == VersionFileRow.version_id)
                    .where(VersionRow.deck_id == deck_id)
                )
            )
            s.execute(delete(DeckRow).where(DeckRow.id == deck_id))
            self._sweep(s, hashes)
        shutil.rmtree(self.scratch / "decks" / deck_id, ignore_errors=True)

    def delete_user(self, sub: str) -> None:
        """The account and, by cascade, every deck it owns and everything under
        them; then the blobs nothing links any more, and the local scratch."""
        with self._tx() as s:
            decks = list(s.scalars(select(DeckRow.id).where(DeckRow.user_id == sub)))
            hashes = set(
                s.scalars(select(DeckFileRow.hash).where(DeckFileRow.deck_id.in_(decks)))
            ) | set(
                s.scalars(
                    select(VersionFileRow.hash)
                    .join(VersionRow, VersionRow.id == VersionFileRow.version_id)
                    .where(VersionRow.deck_id.in_(decks))
                )
            )
            s.execute(delete(UserRow).where(UserRow.id == sub))
            self._sweep(s, hashes)
        for deck_id in decks:
            shutil.rmtree(self.scratch / "decks" / deck_id, ignore_errors=True)
