"""The schema round-trip, the fourteen rejection rules, and the no-styling
backstop. Colocated with the shapes it tests (docs/coderules/structure.md).

Cross-language concerns — the codegen no-diff check, and asserting that the
generated Zod validator agrees with Pydantic on every one of these cases —
live in api/tests/test_schema_codegen.py, since they only exist because of the
language split (docs/coderules/python.md -> "Test").
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from schema.experience import Experience
from schema.json_schema import SCENE_JSON_SCHEMA, serialize_deterministically
from schema.no_style import assert_no_presentational_values

FIXTURES = Path(__file__).parent / "fixtures"
VALID_FIXTURES = ["minimal", "full", "hostile"]


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_fixture_parses_and_round_trips(name: str) -> None:
    data = json.loads((FIXTURES / f"{name}.json").read_text())
    exp = Experience.model_validate(data)

    dumped = exp.model_dump(mode="json", by_alias=True)
    reparsed = Experience.model_validate(dumped)

    assert reparsed.model_dump(by_alias=True) == exp.model_dump(by_alias=True)


def _invalid_cases() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = json.loads(
        (FIXTURES / "invalid_cases.json").read_text()
    )
    return cases


@pytest.mark.parametrize("case", _invalid_cases(), ids=lambda c: str(c["name"]))
def test_each_validation_rule_rejects_its_violation(case: dict[str, object]) -> None:
    """Fourteen rules, fourteen assertions. This is the table that stops a
    rule from being silently deleted later — remove the mutation from
    fixtures/invalid_cases.json and this test starts failing for the right
    reason: the tree it was supposed to reject now passes."""
    with pytest.raises(ValidationError):
        Experience.model_validate(case["data"])


@pytest.mark.parametrize(
    "fragment",
    ["#fff", "1.5rem", "240ms", "rgb(0,0,0)", "cubic-bezier(0.4,0,0.2,1)", "16px"],
)
def test_no_style_walker_rejects_every_presentational_pattern(fragment: str) -> None:
    from lib.result import Err

    tree = {
        "blocks": [{"props": {"type": "body", "text": f"looks like {fragment} here"}}]
    }
    result = assert_no_presentational_values(tree)
    assert isinstance(result, Err)


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_no_style_walker_accepts_every_fixture_unchanged(name: str) -> None:
    from lib.result import Ok

    data = json.loads((FIXTURES / f"{name}.json").read_text())
    result = assert_no_presentational_values(data)
    assert isinstance(result, Ok)


def test_no_style_walker_exempts_slot_code_but_not_its_description() -> None:
    from lib.result import Err, Ok

    exempt = {
        "props": {
            "type": "slot",
            "description": "a demo",
            "html": "<div style='color:#fff'></div>",
            "css": "body{margin:16px}",
            "js": "el.style.transitionDuration='240ms'",
        }
    }
    assert isinstance(assert_no_presentational_values(exempt), Ok)

    leaked = {
        "props": {
            "type": "slot",
            "description": "looks like #fff here",
            "html": "",
            "css": "",
            "js": "",
        }
    }
    assert isinstance(assert_no_presentational_values(leaked), Err)


def test_no_style_walker_exempts_stat_value_but_not_its_label() -> None:
    """The false positive that surfaced from `hostile.json`: "<1ms" is exactly
    the shape of a benchmark number the spec calls legitimate, and exactly the
    shape of a CSS duration the regex exists to catch. `value` is exempt
    because `Stat` has no styling field to leak from; `label` stays covered."""
    from lib.result import Err, Ok

    legitimate = {"props": {"type": "stat", "value": "<1ms", "label": "Latency"}}
    assert isinstance(assert_no_presentational_values(legitimate), Ok)

    leaked = {"props": {"type": "stat", "value": "10x", "label": "Down from 240ms"}}
    assert isinstance(assert_no_presentational_values(leaked), Err)


def test_json_schema_is_deterministic_across_runs_and_a_process_restart() -> None:
    first = serialize_deterministically(
        Experience.model_json_schema(ref_template="#/$defs/{model}")
    )
    second = serialize_deterministically(SCENE_JSON_SCHEMA)
    assert first == second

    import subprocess
    import sys

    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "from schema.json_schema import SCENE_JSON_SCHEMA, serialize_deterministically as s; "
            "print(s(SCENE_JSON_SCHEMA))",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).parent.parent,
    )
    assert out.stdout.strip() == first
