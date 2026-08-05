"""The Director's output shape and its seven pacing rules. Colocated with
the schema it tests (docs/coderules/structure.md).

Small enough (seven rules, no cross-language fixture) that inline cases
read better than a JSON fixture file the way schema/test_scene.py's
fourteen rules need one.
"""

import pytest
from pydantic import ValidationError

from schema.outline import Outline

_HOOK = {"intent": "hook", "beat": "open on the problem", "layoutHint": "centered"}
_PROBLEM = {"intent": "problem", "beat": "name the pain", "layoutHint": "split-left"}
_PROOF = {"intent": "proof", "beat": "show the evidence", "layoutHint": "grid"}
_CTA = {"intent": "cta", "beat": "ask for the click", "layoutHint": "centered"}


def _outline(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "A test outline",
        "scenes": [_HOOK, _PROBLEM, _PROOF, _CTA],
    }
    base.update(overrides)
    return base


def test_a_well_formed_outline_parses() -> None:
    Outline.model_validate(_outline())


@pytest.mark.parametrize(
    ("name", "scenes"),
    [
        ("fewer than 3 scenes", [_HOOK, _CTA]),
        (
            "more than 12 scenes",
            # Alternating intents so this violates only the count, not also
            # the adjacent-repeat rule below — one rule per case.
            [_HOOK]
            + [
                {"intent": ("problem", "reveal", "proof")[i % 3], "beat": f"beat {i}"}
                for i in range(11)
            ]
            + [_CTA],
        ),
        ("zero hooks", [_PROBLEM, _PROOF, _CTA]),
        ("two hooks", [_HOOK, dict(_HOOK, beat="a second hook"), _PROOF, _CTA]),
        ("a hook that is not first", [_PROBLEM, _HOOK, _PROOF, _CTA]),
        ("zero cta scenes", [_HOOK, _PROBLEM, _PROOF]),
        (
            "adjacent scenes repeat intent",
            [_HOOK, _PROBLEM, dict(_PROBLEM, beat="the same problem again"), _CTA],
        ),
    ],
)
def test_each_pacing_rule_rejects_its_violation(
    name: str, scenes: list[dict[str, object]]
) -> None:
    with pytest.raises(ValidationError):
        Outline.model_validate(_outline(scenes=scenes))
