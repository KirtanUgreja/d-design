"""Edit's controls, tested as controls. Mocked seam — no model call.

Each test maps to a line in docs/v1/plan/09-editor.md's Verify section.
"""

from unittest.mock import AsyncMock

import pytest

import features.edit.edit as edit_module
from features.edit import edit_block
from lib.result import Err, Ok, ok
from schema.patch import EditDraft
from schema.scene import Scene

SCENE = Scene.model_validate(
    {
        "id": "s1",
        "intent": "hook",
        "layout": "centered",
        "blocks": [
            {
                "id": "b1",
                "props": {
                    "type": "headline",
                    "text": "Launch with confidence",
                    "emphasis": "hero",
                },
            },
            {"id": "b2", "props": {"type": "body", "text": "Some supporting prose."}},
        ],
    }
)

OWNER = "00000000-0000-4000-8000-00000000000a"
EXPERIENCE = "00000000-0000-4000-8000-0000000000ee"


def _seam(monkeypatch: pytest.MonkeyPatch, draft: EditDraft) -> AsyncMock:
    completion = type("Completion", (), {"value": draft, "repaired": False})()
    mock = AsyncMock(return_value=ok(completion))
    monkeypatch.setattr(edit_module, "complete", mock)
    return mock


async def _edit(
    monkeypatch: pytest.MonkeyPatch, draft: EditDraft, *, block_id: str = "b1"
) -> object:
    _seam(monkeypatch, draft)
    return await edit_block(
        scene=SCENE,
        block_id=block_id,
        instruction="anything",
        owner_id=OWNER,
        experience_id=EXPERIENCE,
    )


def _headline(**over: object) -> EditDraft:
    props = {"type": "headline", "text": "Launch with confidence", "emphasis": "hero"}
    return EditDraft.model_validate({"props": {**props, **over}})


# --- The patch is a diff, not a rewrite -----------------------------------


async def test_only_the_changed_field_leaves_the_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model returns the block's whole props — a partial is an open dict
    and strict structured outputs cannot express one — so the diff here is
    what makes an edit a diff. A patch carrying fields that did not move would
    defeat the client's structural sharing as surely as changing them would."""
    result = await _edit(monkeypatch, _headline(text="Launch boldly"))
    assert isinstance(result, Ok)
    assert result.value.props == {"text": "Launch boldly"}


async def test_an_unchanged_block_produces_an_empty_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = await _edit(monkeypatch, _headline())
    assert isinstance(result, Ok)
    assert result.value.props == {}


async def test_two_changed_fields_both_travel(monkeypatch: pytest.MonkeyPatch) -> None:
    result = await _edit(monkeypatch, _headline(text="Shorter", emphasis="section"))
    assert isinstance(result, Ok)
    assert result.value.props == {"text": "Shorter", "emphasis": "section"}


# --- The refusal is the product's answer ----------------------------------


async def test_a_refusal_is_a_successful_response_with_copy_in_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ "Make the headline smaller" has nowhere to land in `BlockProps`, so what
    comes back is a written sentence offering emphasis instead — not an error,
    not a silent no-op, and not a generic "I can't help with that"
    (docs/v1/plan/09-editor.md -> "Design the absence")."""
    draft = EditDraft.model_validate(
        {
            "props": {
                "type": "headline",
                "text": "Launch with confidence",
                "emphasis": "hero",
            },
            "refusal": "Size comes from the art direction. Set emphasis to section instead.",
        }
    )
    result = await _edit(monkeypatch, draft)
    assert isinstance(result, Ok)
    assert result.value.props == {}
    assert result.value.refusal is not None
    assert "emphasis" in result.value.refusal


# --- Structurally unable to do the dangerous things ------------------------


def test_the_model_has_no_field_for_a_neighbour_or_the_page() -> None:
    """The real control is the shape, not the prompt: there is no scene id, no
    block id, and no list of blocks in `EditDraft`, so an instruction to
    restyle the page or rewrite the next headline has nowhere to go."""
    fields = set(EditDraft.model_fields)
    assert fields == {"props", "refusal"}


def test_the_model_has_no_field_for_any_presentational_value() -> None:
    """Rule 7 seen from Edit's side. `BlockProps` carries no colour, size,
    font, duration or easing, which is why the Edit prompt's "you may not
    change how anything looks" is a fact about the schema rather than a hope
    about the model."""
    from schema.scene import HeadlineProps

    banned = {"color", "colour", "font", "size", "duration", "ease", "weight"}
    assert not banned & set(HeadlineProps.model_fields)


async def test_an_edit_cannot_change_a_block_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What keeps the client's offline whole-tree validation sound: a
    props-only patch that cannot change `type` cannot turn this Body into a
    second Headline in a scene that already has one."""
    draft = EditDraft.model_validate(
        {"props": {"type": "headline", "text": "A second headline"}}
    )
    result = await _edit(monkeypatch, draft, block_id="b2")
    assert isinstance(result, Err)
    assert "type" in result.error.message


async def test_an_unknown_block_is_not_found_rather_than_a_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = await _edit(monkeypatch, _headline(), block_id="nope")
    assert isinstance(result, Err)
    assert result.error.code == "not_found"


async def test_a_refusal_from_the_seam_stays_a_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lib.result import err

    monkeypatch.setattr(
        edit_module, "complete", AsyncMock(return_value=err("refused", "declined"))
    )
    result = await edit_block(
        scene=SCENE,
        block_id="b1",
        instruction="anything",
        owner_id=OWNER,
        experience_id=EXPERIENCE,
    )
    assert isinstance(result, Err)
    assert result.error.code == "refused"
