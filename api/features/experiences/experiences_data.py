"""experiences data access — the feature's SQLAlchemy home (phase 18).

The experiences table (0001 + 0003 + 0009) holds a saved deck (`deck_json`),
its image sidecar (`images_json`) and, once published, the hosted-artefact key
(`published_key`). Every query runs inside the as_user wrapper; RLS
(owner-scoped, 0001) does the isolation — a user only ever sees their own decks.

Saving and publishing are separate operations on purpose. A draft costs
nothing; publishing spends a hosted URL. Folding them together would charge a
free account its single URL for its first save, so the quota gate lives on
`set_published_key` and nowhere else.
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
    images_json: str
    published_key: str | None


def _new_id() -> str:
    return str(uuid.uuid4())


def _record(row: Row[tuple[str, str, str, str, str | None]]) -> ExperienceRecord:
    id_, title, deck_json, images_json, published_key = row
    # Postgres returns a uuid.UUID for the id column, while the dataclass and
    # the response model both say str. Coerce here — the one point both read
    # paths meet. The insert path builds the id in Python (a str), which is why
    # create returned 201 while list and detail 500'd on pydantic validation.
    return ExperienceRecord(
        id=str(id_),
        title=title,
        deck_json=deck_json,
        images_json=images_json,
        published_key=published_key,
    )


@dataclass(frozen=True)
class Forbidden:
    """The write the RLS policy refused — the caller is not the row's owner."""

    detail: str = "not permitted"


async def list_experiences(session: AsyncSession) -> list[ExperienceRecord]:
    """The user's saved decks, newest first. RLS keeps it to their own.

    The payload columns are selected because this list is how the editor opens
    a deck — there is no second fetch. If decks grow large enough for that to
    hurt, the list should return headers only and the detail route carry the
    payload.
    """
    rows = (
        await session.execute(
            text(
                "select id, title, deck_json, images_json, published_key"
                " from experiences order by created_at desc"
            )
        )
    ).all()
    return [_record(r) for r in rows]


async def get_experience(session: AsyncSession, experience_id: str) -> ExperienceRecord | None:
    """One saved deck. RLS returns no row for another user's."""
    row = (
        await session.execute(
            text(
                "select id, title, deck_json, images_json, published_key"
                " from experiences where id = :id"
            ),
            {"id": experience_id},
        )
    ).first()
    return _record(row) if row is not None else None


async def save_experience(
    session: AsyncSession,
    *,
    title: str,
    deck_json: str,
    images_json: str = "{}",
    published_key: str | None = None,
) -> Result[ExperienceRecord, Forbidden]:
    """Create a draft. RLS's with check enforces ownership.

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
                "insert into experiences"
                " (id, owner_id, title, deck_json, images_json, published_key)"
                " values (:id, current_setting('app.user_id')::uuid,"
                " :title, :deck, :images, :published)"
            ),
            {
                "id": experience_id,
                "title": title,
                "deck": deck_json,
                "images": images_json,
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
            images_json=images_json,
            published_key=published_key,
        )
    )


async def update_experience(
    session: AsyncSession,
    experience_id: str,
    *,
    title: str,
    deck_json: str,
    images_json: str,
) -> Result[ExperienceRecord | None, Forbidden]:
    """Update a draft in place.

    Returns ``Ok(None)`` when no row matched. That is the RLS refusal's other
    shape: an UPDATE whose ``using`` clause excludes the row changes nothing
    and raises nothing, so "no row" is how a non-owner's write is refused — and
    the route answers 404 rather than leaking that the row exists.
    """
    try:
        row = (
            await session.execute(
                text(
                    "update experiences"
                    " set title = :title, deck_json = :deck, images_json = :images"
                    " where id = :id"
                    " returning id, title, deck_json, images_json, published_key"
                ),
                {"id": experience_id, "title": title, "deck": deck_json, "images": images_json},
            )
        ).first()
    except DBAPIError as exc:
        if is_rls_refusal(exc):
            return err(Forbidden())
        raise
    return ok(_record(row) if row is not None else None)


async def set_published_key(
    session: AsyncSession,
    experience_id: str,
    *,
    published_key: str,
) -> Result[ExperienceRecord | None, Forbidden]:
    """Record the hosted artefact's key. The caller has already spent the quota.

    Same ``Ok(None)`` shape as update: no row matched means the policy excluded
    it, which is a 404 at the route.
    """
    try:
        row = (
            await session.execute(
                text(
                    "update experiences set published_key = :key"
                    " where id = :id"
                    " returning id, title, deck_json, images_json, published_key"
                ),
                {"id": experience_id, "key": published_key},
            )
        ).first()
    except DBAPIError as exc:
        if is_rls_refusal(exc):
            return err(Forbidden())
        raise
    return ok(_record(row) if row is not None else None)
