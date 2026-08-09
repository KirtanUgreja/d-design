"""Publish's own feature tests — create/get/replace/publish/unpublish through
the public surface, plus the isolation and published-at-filter checks that
are this phase's actual security surface (docs/security/testing.md).
"""

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from db.tenant import as_user
from features.publish import (
    create_experience,
    get_experience,
    publish_experience,
    replace_experience,
    unpublish_experience,
)
from features.publish.publish_data import find_published_by_id
from lib.result import Err, Ok
from schema.experience import Experience

FIXTURES = Path(__file__).resolve().parent.parent.parent / "schema" / "fixtures"
USER_A = "00000000-0000-4000-8000-00000000000a"
USER_B = "00000000-0000-4000-8000-00000000000b"


def _minimal() -> Experience:
    data = json.loads((FIXTURES / "minimal.json").read_text())
    return Experience.model_validate(data)


@pytest.fixture(autouse=True)
async def _cleanup() -> AsyncIterator[None]:
    yield
    engine = create_async_engine(os.environ["MIGRATION_DATABASE_URL"])
    async with engine.begin() as conn:
        await conn.execute(
            text("delete from experiences where owner_id in (:a, :b)"),
            {"a": USER_A, "b": USER_B},
        )
    await engine.dispose()


async def test_create_and_get_round_trip() -> None:
    created = await create_experience(USER_A, _minimal())
    assert isinstance(created, Ok)
    assert created.value.title == "Minimal Experience"
    assert created.value.meta.published_at is None

    fetched = await get_experience(USER_A, created.value.id)
    assert isinstance(fetched, Ok)
    assert fetched.value.id == created.value.id
    assert fetched.value.title == "Minimal Experience"


async def test_a_uuid_the_caller_proposes_becomes_the_row_id() -> None:
    """`/new` writes every `generations` row for a build session against an id
    it mints before Intake, then creates the experience under that same id. If
    the server silently reassigned it, the cost log for a build could never be
    joined to what it built — which is the log's only purpose."""
    proposed = "11111111-2222-4333-8444-555555555555"
    created = await create_experience(
        USER_A, _minimal().model_copy(update={"id": proposed})
    )
    assert isinstance(created, Ok)
    assert created.value.id == proposed


async def test_a_non_uuid_id_is_ignored_rather_than_rejected() -> None:
    """The fixtures carry human ids ("exp-minimal") and always have. An id the
    id column has no representation for is a name, not an error."""
    created = await create_experience(USER_A, _minimal())
    assert isinstance(created, Ok)
    assert created.value.id != "exp-minimal"


async def test_get_unknown_id_is_not_found() -> None:
    result = await get_experience(USER_A, "00000000-0000-0000-0000-000000000000")
    assert isinstance(result, Err)
    assert result.error.code == "not_found"


async def test_get_malformed_id_is_not_found_not_a_500() -> None:
    result = await get_experience(USER_A, "not-a-uuid")
    assert isinstance(result, Err)
    assert result.error.code == "not_found"


async def test_a_second_user_cannot_read_the_row() -> None:
    """RLS, seen from the feature layer rather than raw SQL — the same
    guarantee test_tenancy.py proves generically, exercised through the
    actual code path a route uses."""
    created = await create_experience(USER_A, _minimal())
    assert isinstance(created, Ok)

    result = await get_experience(USER_B, created.value.id)
    assert isinstance(result, Err)
    assert result.error.code == "not_found"


async def test_replace_changes_content() -> None:
    created = await create_experience(USER_A, _minimal())
    assert isinstance(created, Ok)

    edited = created.value.model_copy(update={"title": "Edited Title"})
    replaced = await replace_experience(USER_A, created.value.id, edited)
    assert isinstance(replaced, Ok)
    assert replaced.value.title == "Edited Title"

    fetched = await get_experience(USER_A, created.value.id)
    assert isinstance(fetched, Ok)
    assert fetched.value.title == "Edited Title"


async def test_publish_then_unpublish() -> None:
    created = await create_experience(USER_A, _minimal())
    assert isinstance(created, Ok)
    experience_id = created.value.id

    published = await publish_experience(USER_A, experience_id)
    assert isinstance(published, Ok)
    assert published.value.meta.published_at is not None

    unpublished = await unpublish_experience(USER_A, experience_id)
    assert isinstance(unpublished, Ok)
    assert unpublished.value.meta.published_at is None


async def test_published_at_filter_only_matches_after_publish() -> None:
    from uuid import UUID

    created = await create_experience(USER_A, _minimal())
    assert isinstance(created, Ok)
    experience_id = UUID(created.value.id)

    async with as_user(USER_A) as session:
        assert await find_published_by_id(session, experience_id) is None

    published = await publish_experience(USER_A, created.value.id)
    assert isinstance(published, Ok)

    async with as_user(USER_A) as session:
        row = await find_published_by_id(session, experience_id)
        assert row is not None
        assert row.id == experience_id
