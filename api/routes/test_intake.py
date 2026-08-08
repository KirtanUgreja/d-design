"""The two brief routes, which are the ones that carry a decision rather than
just glue.

Handlers called directly rather than over HTTP: they are plain async functions,
and the repo has no TestClient harness because routes are thin enough to be
tested through their features (docs/coderules/structure.md). What is asserted
here is the part that is *not* in a feature — the 404 before a brief exists,
and the deliberate absence of the claims check on the user's own edit.
"""

import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import config
from db.tenant import as_user
from features.intake import save_brief
from routes.intake import read_brief, replace_brief
from schema.brief import Brief, BriefCta

_MIGRATOR = os.environ["MIGRATION_DATABASE_URL"]


def _brief(**overrides: object) -> Brief:
    base = {
        "goal": "Launch our observability platform",
        "audience": "Backend engineers at mid-size SaaS companies",
        "key_messages": [
            "See every request in one trace",
            "Setup takes ten minutes",
            "It cuts MTTR by 68%",
        ],
        "proof_points": ["It cuts MTTR by 68%"],
        "tone": "confident, technical",
        "cta": BriefCta(label="Start free trial", href="https://example.com/trial"),
    }
    return Brief.model_validate({**base, **overrides})


@pytest.fixture
async def clean_briefs() -> AsyncIterator[None]:
    engine = create_async_engine(_MIGRATOR)
    async with engine.begin() as conn:
        await conn.execute(text("delete from briefs"))
    yield
    async with engine.begin() as conn:
        await conn.execute(text("delete from briefs"))
    await engine.dispose()


async def test_reading_a_brief_that_does_not_exist_is_a_404(
    clean_briefs: None,
) -> None:
    """Not an empty Brief and not a 500. The Intake screen asks for a stored
    brief before the interview has produced one, and "there isn't one yet" is
    an ordinary answer."""
    with pytest.raises(HTTPException) as caught:
        await read_brief(uuid4())
    assert caught.value.status_code == 404


async def test_a_saved_brief_reads_back(clean_briefs: None) -> None:
    experience_id = uuid4()
    owner_id = UUID(config().local_user_id)
    brief = _brief()

    async with as_user(str(owner_id)) as session:
        await save_brief(
            session, owner_id=owner_id, experience_id=experience_id, brief=brief
        )

    assert await read_brief(experience_id) == brief


async def test_the_users_own_edit_is_not_claims_checked(clean_briefs: None) -> None:
    """The rule, stated as a test so it is not "fixed" later:
    `features/intake/checks.py` exists to stop the *model* rewording the
    user's copy. Text the user typed is approved by definition, and running
    the check here would be the product telling a marketer they may not say
    what they mean.

    The edited message below traces to nothing the interview ever saw, which
    is exactly the input `check_draft` rejects on the model's path.
    """
    experience_id = uuid4()
    edited = _brief(key_messages=["A claim nobody typed before now", "Two", "Three"])

    assert await replace_brief(experience_id, edited) == edited
    assert await read_brief(experience_id) == edited


async def test_the_href_allowlist_still_applies_to_an_edit(clean_briefs: None) -> None:
    """The one thing the user's own text does not get a pass on. `BriefCta`
    parses at entry on this route exactly as on the interview path, so a
    pasted `javascript:` URL never reaches the table — FastAPI rejects the
    body before `replace_brief` is ever entered.

    A raw dict, not a `BriefCta`: that is what the route actually receives,
    and it is also the only form that validates. Pydantic passes an existing
    model instance through untouched, so building the bad value with
    `model_construct` and handing it over would prove nothing.
    """
    import pydantic

    for href in ("javascript:alert(1)", "data:text/html,x", "//evil.example"):
        with pytest.raises(pydantic.ValidationError):
            _brief(cta={"label": "Go", "href": href})


async def test_the_newest_brief_wins(clean_briefs: None) -> None:
    """Re-running the interview, or saving an edit, is how a user corrects a
    brief — so a read has to return the latest, not the first."""
    experience_id = uuid4()

    await replace_brief(experience_id, _brief(goal="First goal"))
    await replace_brief(experience_id, _brief(goal="Second goal"))

    assert (await read_brief(experience_id)).goal == "Second goal"
