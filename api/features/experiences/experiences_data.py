"""experiences data access — the feature's SQLAlchemy home (phase 18).

The experiences table (0001 + 0003) holds a saved deck (deck_json) and, once
published, the hosted-artefact key (published_key). Every query runs inside
the as_user wrapper; RLS (owner-scoped, 0001) does the isolation — a user
only ever sees their own decks.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.exc import DBAPIError

from db.errors import is_rls_refusal
from lib.result import Result, err, ok

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ExperienceRecord:
    id: str
    title: str
    deck_json: str
    published_key: str | None


def _new_id() -> str:
    return str(uuid.uuid4())


def _record(row: Row[tuple[str, str, str, str | None]]) -> ExperienceRecord:
    id_, title, deck_json, published_key = row
    # Postgres returns a uuid.UUID for the id column, while the dataclass and
    # the response model both say str. Coerce here — the one point both read
    # paths meet. The insert path builds the id in Python (a str), which is why
    # create returned 201 while list and detail 500'd on pydantic validation.
    return ExperienceRecord(
        id=str(id_), title=title, deck_json=deck_json, published_key=published_key
    )


async def list_experiences(session: AsyncSession) -> list[ExperienceRecord]:
    """The user's saved decks, newest first. RLS keeps it to their own."""
    rows = (
        await session.execute(
            text(
                "select id, title, deck_json, published_key"
                " from experiences order by created_at desc"
            )
        )
    ).all()
    return [_record(r) for r in rows]


async def get_experience(session: AsyncSession, experience_id: str) -> ExperienceRecord | None:
    """One saved deck. RLS returns no row for another user's."""
    row = (
        await session.execute(
            text("select id, title, deck_json, published_key from experiences where id = :id"),
            {"id": experience_id},
        )
    ).first()
    return _record(row) if row is not None else None


@dataclass(frozen=True)
class Forbidden:
    """The write the RLS policy refused — the caller is not the row's owner."""

    detail: str = "not permitted"


async def save_experience(
    session: AsyncSession,
    *,
    title: str,
    deck_json: str,
    published_key: str | None,
) -> Result[ExperienceRecord, Forbidden]:
    """Save (or update) a deck. RLS's with check enforces ownership.

    ``owner_id`` comes from the session's ``app.user_id`` (set by ``as_user``).
    It must be set on the row: the column is NOT NULL and the with check
    compares against it — an insert without it is both a 500 (live-run finding)
    and a policy violation.

    A refusal by the policy is an expected authorization failure, so it returns
    ``Err`` and the route answers 403 rather than a 500.
    """
    experience_id = _new_id()
    try:
        await session.execute(
            text(
                "insert into experiences (id, owner_id, title, deck_json, published_key)"
                " values (:id, current_setting('app.user_id')::uuid, :title, :deck, :published)"
            ),
            {
                "id": experience_id,
                "title": title,
                "deck": deck_json,
                "published": published_key,
            },
        )
    except DBAPIError as exc:
        if is_rls_refusal(exc):
            return err(Forbidden())
        raise
    return ok(
        ExperienceRecord(
            id=experience_id,
            title=title,
            deck_json=deck_json,
            published_key=published_key,
        )
    )
