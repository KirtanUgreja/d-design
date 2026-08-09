"""SQLAlchemy for `brands`. The ORM lives in a feature data module and nowhere
else (docs/coderules/patterns.md rule 8).

One brand per owner in v1 — the brand kit is a primitive, not a library of
themes — so a save is an upsert against whatever row this owner already has.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Brand
from schema.experience import BrandKit


async def load_brand(session: AsyncSession) -> BrandKit | None:
    """Scoped by the RLS policy through `as_user`, not by a filter here
    (rule 9). Newest wins, which only matters if a second row ever appears."""
    row = (
        await session.execute(select(Brand).order_by(Brand.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    return None if row is None else _as_kit(row)


async def save_brand(
    session: AsyncSession, *, owner_id: UUID, kit: BrandKit
) -> BrandKit:
    row = (
        await session.execute(select(Brand).order_by(Brand.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    if row is None:
        row = Brand(owner_id=owner_id)
        session.add(row)
    row.display_font = kit.display_font
    row.text_font = kit.text_font
    row.primary = kit.primary
    row.secondary = kit.secondary
    row.neutral = kit.neutral
    row.logo_asset_id = UUID(kit.logo_asset_id) if kit.logo_asset_id else None
    await session.flush()
    return _as_kit(row)


def _as_kit(row: Brand) -> BrandKit:
    return BrandKit(
        id=str(row.id),
        # Narrowed on the way out rather than trusted: the column is `String`,
        # and `FontId` is the allowlist. A row written before the Literal
        # existed, or by hand, falls back rather than failing a page load.
        display_font="fraunces" if row.display_font != "inter" else "inter",
        text_font="fraunces" if row.text_font == "fraunces" else "inter",
        primary=row.primary,
        secondary=row.secondary,
        neutral=row.neutral,
        logo_asset_id=str(row.logo_asset_id) if row.logo_asset_id else None,
    )
