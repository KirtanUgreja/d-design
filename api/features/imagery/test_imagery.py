"""Generated imagery: the cap, the prompt boundary, and the marking.

The provider call is not built (see `imagery.py`'s ponytail), so these test the
three things that exist and are the three the exit gate actually names: the cap
fails closed, the prompt cannot reach the product, and a generated asset is
marked as one.
"""

import io

import pytest
from PIL import Image

from features.imagery import (
    MAX_GENERATED_PER_EXPERIENCE,
    build_imagery_prompt,
    check_generation_cap,
    store_generated_image,
)
from lib.result import Err, Ok


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), (12, 34, 56)).save(buffer, format="PNG")
    return buffer.getvalue()


# --- The cap ---------------------------------------------------------------


@pytest.mark.parametrize("existing", [0, 1, MAX_GENERATED_PER_EXPERIENCE - 1])
def test_under_the_cap_is_allowed(existing: int) -> None:
    assert isinstance(check_generation_cap(existing), Ok)


@pytest.mark.parametrize(
    "existing", [MAX_GENERATED_PER_EXPERIENCE, MAX_GENERATED_PER_EXPERIENCE + 10]
)
def test_at_or_over_the_cap_is_refused(existing: int) -> None:
    """Generated imagery is the one place v1's cost model stops being a
    rounding error — docs/v1/ai-pipeline.md: "generated imagery, storage,
    bandwidth, and human review time all exceed" token cost."""
    result = check_generation_cap(existing)
    assert isinstance(result, Err)
    assert result.error.code == "quota_exceeded"


def test_the_cap_takes_a_count_rather_than_fetching_one() -> None:
    """Fails closed by signature: a caller that cannot produce a count cannot
    slip past with a default of zero. Same reasoning as the quota check, where
    an unreadable quota refuses rather than permits."""
    import inspect

    assert list(inspect.signature(check_generation_cap).parameters) == [
        "existing_generated"
    ]


# --- Never generate the product -------------------------------------------


def test_the_prompt_cannot_reach_what_the_product_is() -> None:
    """Structural rather than a wording check. The builder takes a scene
    intent, a beat and a tone — there is no parameter for key messages or
    proof points, so "never generate the product" is a fact about the
    signature rather than an instruction that has to hold."""
    import inspect

    assert set(inspect.signature(build_imagery_prompt).parameters) == {
        "scene_intent",
        "scene_beat",
        "tone",
    }


def test_the_prompt_says_so_as_well() -> None:
    """Belt and braces: the signature makes depicting the product impossible to
    *ask for* from the brief, and this makes it explicit for the beat, which is
    narrative text and could describe one."""
    prompt = build_imagery_prompt(
        scene_intent="reveal", scene_beat="show the dashboard", tone="confident"
    )
    lowered = prompt.lower()
    for banned in ("product", "device", "screen", "logo", "person"):
        assert banned in lowered, f"the prompt should forbid depicting a {banned}"
    assert "do not depict" in lowered


# --- Mark it ---------------------------------------------------------------


async def test_a_generated_image_is_stored_marked_and_verified() -> None:
    """Through the *same* pipeline an upload takes — same magic-byte check,
    same re-encode, same server-generated key — because a second path is a
    second place to get it wrong. And `source='generated'`, which is the field
    a marketer checks before publishing."""
    from db.tenant import as_user
    from features.assets import list_assets

    owner = "00000000-0000-4000-8000-00000000000a"
    result = await store_generated_image(
        raw=_png(), owner_id=owner, alt="Atmospheric texture"
    )
    assert isinstance(result, Ok)
    assert result.value.source == "generated"
    assert result.value.storage_key.startswith("assets/")
    assert result.value.width == 32 and result.value.height == 24

    async with as_user(owner) as session:
        stored = await list_assets(session)
    mine = next(a for a in stored if a.id == result.value.id)
    assert mine.source == "generated"


async def test_bytes_that_are_not_an_image_are_refused_like_any_upload() -> None:
    """The provider is trusted less than the code that calls it."""
    result = await store_generated_image(
        raw=b"<?php ?>" + b"\x00" * 32,
        owner_id="00000000-0000-4000-8000-00000000000a",
        alt="x",
    )
    assert isinstance(result, Err)
