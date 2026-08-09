"""`assets` and `brands` isolation, the same shape as tests/test_tenancy.py.

Both tables' policies were created in the same migration as the table, so this
proves the policy rather than the intent — the failure it guards against is one
deploy in which a table existed without its policy and was readable across
tenants for the length of that deploy.
"""

import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from db.tenant import as_user
from features.assets import list_assets, save_asset
from features.brand import load_brand, save_brand
from schema.experience import BrandKit

_MIGRATOR = os.environ["MIGRATION_DATABASE_URL"]

USER_A = UUID("00000000-0000-4000-8000-00000000000a")
USER_B = UUID("00000000-0000-4000-8000-00000000000b")


@pytest.fixture
async def clean() -> AsyncIterator[None]:
    engine = create_async_engine(_MIGRATOR)
    async with engine.begin() as conn:
        await conn.execute(text("delete from assets"))
        await conn.execute(text("delete from brands"))
    yield
    async with engine.begin() as conn:
        await conn.execute(text("delete from assets"))
        await conn.execute(text("delete from brands"))
    await engine.dispose()


async def _add_asset(owner: UUID, alt: str) -> None:
    async with as_user(str(owner)) as session:
        await save_asset(
            session,
            owner_id=owner,
            kind="image",
            storage_key=f"assets/{uuid4()}",
            mime="image/png",
            width=10,
            height=10,
            alt=alt,
            source="upload",
        )


async def test_one_owners_assets_are_invisible_to_another(clean: None) -> None:
    await _add_asset(USER_A, "A's product shot")
    await _add_asset(USER_B, "B's product shot")

    async with as_user(str(USER_A)) as session:
        mine = await list_assets(session)
    assert [a.alt for a in mine] == ["A's product shot"]


async def test_a_tenant_cannot_insert_an_asset_owned_by_someone_else(
    clean: None,
) -> None:
    """`using` alone would filter reads and leave this open — the `with check`
    half of the policy is what refuses it."""
    with pytest.raises(DBAPIError):
        async with as_user(str(USER_A)) as session:
            await save_asset(
                session,
                owner_id=USER_B,
                kind="image",
                storage_key=f"assets/{uuid4()}",
                mime="image/png",
                width=1,
                height=1,
                alt="planted",
                source="upload",
            )


def _kit(primary: str) -> BrandKit:
    return BrandKit(
        id="ignored-on-save",
        display_font="fraunces",
        text_font="inter",
        primary=primary,
        secondary="#222222",
        neutral="#888888",
    )


async def test_one_owners_brand_is_invisible_to_another(clean: None) -> None:
    async with as_user(str(USER_A)) as session:
        await save_brand(session, owner_id=USER_A, kit=_kit("#aa0000"))
    async with as_user(str(USER_B)) as session:
        await save_brand(session, owner_id=USER_B, kit=_kit("#0000bb"))

    async with as_user(str(USER_A)) as session:
        mine = await load_brand(session)
    assert mine is not None
    assert mine.primary == "#aa0000"


async def test_saving_a_brand_twice_updates_rather_than_accumulates(
    clean: None,
) -> None:
    """One brand per owner in v1 — the kit is a primitive, not a library of
    themes — so the second save is the same row."""
    async with as_user(str(USER_A)) as session:
        first = await save_brand(session, owner_id=USER_A, kit=_kit("#aa0000"))
    async with as_user(str(USER_A)) as session:
        second = await save_brand(session, owner_id=USER_A, kit=_kit("#00aa00"))
    assert first.id == second.id
    assert second.primary == "#00aa00"


async def test_a_font_can_only_be_a_registry_id(clean: None) -> None:
    """The exit gate's "a raw family string is rejected", proven where it is
    actually enforced: `FontId` is a `Literal`, so `BrandKit` has no
    representation for a family name — it is a parse failure, not a check."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        BrandKit(
            id="b",
            display_font="Helvetica; } * { display: none }",  # type: ignore[arg-type]
            text_font="inter",
            primary="#aa0000",
            secondary="#222222",
            neutral="#888888",
        )
