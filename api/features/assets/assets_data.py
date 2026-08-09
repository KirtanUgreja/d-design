"""SQLAlchemy for `assets`. The ORM lives in a feature data module and nowhere
else (docs/coderules/patterns.md rule 8).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AssetRow
from schema.experience import Asset


async def save_asset(
    session: AsyncSession,
    *,
    owner_id: UUID,
    kind: str,
    storage_key: str,
    mime: str,
    width: int | None,
    height: int | None,
    alt: str | None,
    source: str,
) -> AssetRow:
    row = AssetRow(
        owner_id=owner_id,
        kind=kind,
        storage_key=storage_key,
        mime=mime,
        width=width,
        height=height,
        alt=alt,
        source=source,
    )
    session.add(row)
    # The id is server-generated, and the caller needs it to hand an `Asset`
    # back. Flushing here rather than making every caller remember to.
    await session.flush()
    return row


async def list_assets(session: AsyncSession) -> list[Asset]:
    """No `owner_id` filter, and that is not an oversight: every caller reaches
    this through `as_user`, so the RLS policy on `assets` is what scopes the
    read. A second filter in Python would imply the policy is optional
    (docs/coderules/patterns.md rule 9)."""
    rows = (
        (await session.execute(select(AssetRow).order_by(AssetRow.created_at.desc())))
        .scalars()
        .all()
    )
    return [_as_asset(r) for r in rows]


async def get_asset(session: AsyncSession, asset_id: UUID) -> Asset | None:
    row = (
        await session.execute(select(AssetRow).where(AssetRow.id == asset_id))
    ).scalar_one_or_none()
    return None if row is None else _as_asset(row)


def _as_asset(row: AssetRow) -> Asset:
    return Asset(
        id=str(row.id),
        kind="video" if row.kind == "video" else "image",
        storage_key=row.storage_key,
        mime=row.mime,
        width=row.width,
        height=row.height,
        alt=row.alt,
        source="generated" if row.source == "generated" else "upload",
    )


async def find_by_storage_key(session: AsyncSession, storage_key: str) -> Asset | None:
    """The serving route's lookup, and its path-traversal guard.

    A key is matched against a column, never joined onto a path, so `../`
    resolves to no row rather than to a file. That is the whole defence: there
    is no filesystem join here to escape from.
    """
    row = (
        await session.execute(
            select(AssetRow).where(AssetRow.storage_key == storage_key)
        )
    ).scalar_one_or_none()
    return None if row is None else _as_asset(row)
