"""check_outline's two rules: every scene has a layoutHint, and no two
adjacent scenes repeat one (docs/v1/plan/07-director.md -> "Assign
layoutHint here, not in Build"). Pure, no DB, no model call.
"""

from features.director.checks import check_outline
from lib.result import Err, Ok
from schema.outline import Outline, OutlineScene


def _scene(intent: str, layout_hint: str | None) -> OutlineScene:
    return OutlineScene.model_validate(
        {"intent": intent, "beat": "does something", "layoutHint": layout_hint}
    )


def test_valid_outline_passes() -> None:
    outline = Outline(
        title="t",
        scenes=[
            _scene("hook", "centered"),
            _scene("problem", "split-left"),
            _scene("proof", "grid"),
            _scene("cta", "centered"),
        ],
    )
    assert isinstance(check_outline(outline), Ok)


def test_missing_layout_hint_rejected() -> None:
    outline = Outline(
        title="t",
        scenes=[
            _scene("hook", "centered"),
            _scene("problem", None),
            _scene("proof", "grid"),
            _scene("cta", "centered"),
        ],
    )
    result = check_outline(outline)
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"


def test_adjacent_repeated_layout_hint_rejected() -> None:
    outline = Outline(
        title="t",
        scenes=[
            _scene("hook", "centered"),
            _scene("problem", "split-left"),
            _scene("proof", "split-left"),
            _scene("cta", "centered"),
        ],
    )
    result = check_outline(outline)
    assert isinstance(result, Err)
    assert result.error.code == "invalid_input"
