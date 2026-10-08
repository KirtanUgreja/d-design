"""The `app` database's tables (phase 29). Only ``store/sql.py`` queries them;
Alembic (``migrations/``) creates them.

Times are stored as naive UTC. Deleting a user cascades to their decks and
everything under them (database-level ``ON DELETE CASCADE``); a blob is
removed by the store once no deck or version links it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# JSONB on Postgres, JSON text on SQLite (local runs and offline tests).
Json = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(Text, primary_key=True)  # Better Auth's JWT `sub`
    email: Mapped[str] = mapped_column(Text, default="")
    name: Mapped[str] = mapped_column(Text, default="")
    avatar: Mapped[dict[str, object]] = mapped_column(Json)
    created: Mapped[datetime] = mapped_column(DateTime)


class DeckRow(Base):
    __tablename__ = "decks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # Nullable only for local runs without accounts.
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    data: Mapped[dict[str, object]] = mapped_column(Json)  # the Deck
    version: Mapped[int] = mapped_column(Integer)
    aborted: Mapped[bool] = mapped_column(Boolean, default=False)
    history_at: Mapped[int] = mapped_column(Integer, default=-1)  # History.at
    created: Mapped[datetime] = mapped_column(DateTime)
    updated: Mapped[datetime] = mapped_column(DateTime, index=True)


def _deck_fk() -> Mapped[str]:
    return mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), primary_key=True)


class QuestionsRow(Base):
    __tablename__ = "questions"
    deck_id: Mapped[str] = _deck_fk()
    data: Mapped[list[dict[str, object]]] = mapped_column(Json)


class EventRow(Base):
    __tablename__ = "events"
    deck_id: Mapped[str] = _deck_fk()
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[dict[str, object]] = mapped_column(Json)


class LedgerRow(Base):
    """One model call: ids, sizes, timings and cost, never content. Every row
    carries the deck owner's ``user_id`` (the per-user cap, credits later)."""

    __tablename__ = "ledger"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # SET NULL, not CASCADE: spend outlives a deck, so the daily cap does too.
    deck_id: Mapped[str | None] = mapped_column(
        ForeignKey("decks.id", ondelete="SET NULL"), index=True
    )
    at: Mapped[datetime] = mapped_column(DateTime, index=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    data: Mapped[dict[str, object]] = mapped_column(Json)  # the LedgerEntry


class KeptRow(Base):
    __tablename__ = "kept"
    deck_id: Mapped[str] = _deck_fk()
    slide_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    html: Mapped[str] = mapped_column(Text)
    css: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text)


class VersionRow(Base):
    """A labelled snapshot (phase 28 undo): the deck, its kept slides, and the
    files it linked (``version_files``). ``n`` is its place in History.labels."""

    __tablename__ = "versions"
    __table_args__ = (Index("ix_versions_deck_n", "deck_id", "n"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deck_id: Mapped[str] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"))
    n: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(Text)
    deck: Mapped[dict[str, object]] = mapped_column(Json)
    kept: Mapped[dict[str, object]] = mapped_column(Json)  # slide id -> {html, css, origin}


class BlobRow(Base):
    """Screenshots, exports, PDFs and uploads, stored once by content hash."""

    __tablename__ = "blobs"
    hash: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 hex
    data: Mapped[bytes] = mapped_column(LargeBinary)
    content_type: Mapped[str] = mapped_column(Text)
    size: Mapped[int] = mapped_column(Integer)


class DeckFileRow(Base):
    """A deck's current files: ``slides/<sid>.png``, ``export-present.html``, ..."""

    __tablename__ = "deck_files"
    deck_id: Mapped[str] = _deck_fk()
    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    hash: Mapped[str] = mapped_column(ForeignKey("blobs.hash"), index=True)


class VersionFileRow(Base):
    __tablename__ = "version_files"
    version_id: Mapped[int] = mapped_column(
        ForeignKey("versions.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    hash: Mapped[str] = mapped_column(ForeignKey("blobs.hash"), index=True)


class JobRow(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_state_created", "state", "created"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    deck_id: Mapped[str] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str | None] = mapped_column(Text)  # the deck's owner, for the worker
    state: Mapped[str] = mapped_column(String(8))  # queued, running, done
    created: Mapped[float] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[str] = mapped_column(Text, default="")
    beat: Mapped[float | None] = mapped_column(Float)
