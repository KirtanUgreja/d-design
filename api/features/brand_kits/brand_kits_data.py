"""brand_kits data access — the feature's SQLAlchemy home (phase 17).

The ORM-invariant-compliant module: SQLAlchemy appears here (and in db/,
migrations/, tests/), nowhere else. Every query runs inside the as_user
wrapper so RLS (the team-scoped policies from 0002) does the isolation — this
module never filters by user itself; it relies on the session variable, which
fails closed when unset.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.engine import Row

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class BrandKitRecord:
    id: str
    team_id: str
    name: str
    colors: dict[str, str]
    logo_ref: str | None
    font_ids: list[str]


def _new_id() -> str:
    return str(uuid.uuid4())


# The six columns every kit query selects, in order.
_KitRow = tuple[str, str, str, str, str | None, str]


def _record(row: Row[_KitRow]) -> BrandKitRecord:
    id_, team_id, name, colors_json, logo_ref, font_ids = row
    colors = json.loads(colors_json) if colors_json else {}
    fonts = json.loads(font_ids) if font_ids else []
    return BrandKitRecord(
        id=id_, team_id=team_id, name=name, colors=colors, logo_ref=logo_ref, font_ids=fonts
    )


async def list_kits_for_team(session: AsyncSession, team_id: str) -> list[BrandKitRecord]:
    """List the kits in a team. RLS denies rows the user is not a member of."""
    rows = (
        await session.execute(
            text(
                "select id, team_id, name, colors_json, logo_ref, font_ids"
                " from brand_kits where team_id = :team_id order by created_at"
            ),
            {"team_id": team_id},
        )
    ).all()
    return [_record(r) for r in rows]


async def get_kit(session: AsyncSession, kit_id: str) -> BrandKitRecord | None:
    """Get one kit. RLS returns no row for a kit whose team the user is not in."""
    row = (
        await session.execute(
            text(
                "select id, team_id, name, colors_json, logo_ref, font_ids"
                " from brand_kits where id = :kit_id"
            ),
            {"kit_id": kit_id},
        )
    ).first()
    return _record(row) if row is not None else None


async def create_kit(
    session: AsyncSession,
    *,
    team_id: str,
    name: str,
    colors: dict[str, str],
    logo_ref: str | None,
    font_ids: list[str],
) -> BrandKitRecord:
    """Create a kit. RLS's with check enforces the user is a team member —
    a non-member's insert is rejected by the database, not by this module."""
    kit_id = _new_id()
    await session.execute(
        text(
            "insert into brand_kits (id, team_id, name, colors_json, logo_ref, font_ids)"
            " values (:id, :team_id, :name, :colors, :logo_ref, :font_ids)"
        ),
        {
            "id": kit_id,
            "team_id": team_id,
            "name": name,
            "colors": json.dumps(colors),
            "logo_ref": logo_ref,
            "font_ids": json.dumps(font_ids),
        },
    )
    return BrandKitRecord(
        id=kit_id, team_id=team_id, name=name, colors=colors, logo_ref=logo_ref, font_ids=font_ids
    )


async def list_teams(session: AsyncSession) -> list[tuple[str, str]]:
    """List the teams the user can see (owns or is a member of). Returns
    (id, name). RLS: teams is owner-scoped, team_members is team-scoped."""
    rows = (
        await session.execute(
            text(
                "select t.id, t.name from teams t"
                " join team_members tm on tm.team_id = t.id"
                " where tm.user_id = current_setting('app.user_id')::uuid"
                " order by t.created_at"
            )
        )
    ).all()
    return [(r[0], r[1]) for r in rows]
