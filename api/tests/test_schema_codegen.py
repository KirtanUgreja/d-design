"""The tests that only exist because of the language split.

All three are cheap, and between them they are the whole reason "one source of
truth" survives a language boundary (docs/coderules/python.md -> "Test").
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from schema.experience import Experience

API = Path(__file__).resolve().parent.parent
FIXTURES = API / "schema" / "fixtures"
VALID_FIXTURES = ["minimal", "full", "hostile"]


def _all_cases() -> list[dict[str, object]]:
    """Every fixture, valid and invalid, in the one shape both languages read.
    The three valid trees also serve phase 04 (render) and phase 06 (compare) —
    they are not duplicated for this test, only wrapped.

    Only the WIRE-representable invalid cases belong here — the ones JSON
    Schema can actually express as a field's shape (a length cap, an item
    count, a pattern). The other nine of the fourteen rejection rules need to
    count, order, or cross-reference across sibling fields or nested arrays
    ("exactly one hook and it is first", "at least one CTA somewhere", "ids
    unique across this list") — JSON Schema validates one node's shape and has
    no vocabulary for a predicate over a whole tree. That is not a gap in the
    emitter; it is what the format is, discovered by this exact test on the
    first real schema it ran against. Those nine are asserted Python-only, in
    api/schema/test_scene.py, against the same source file
    (fixtures/invalid_cases.json) this one reads a subset of.
    """
    cases = [
        {
            "name": name,
            "valid": True,
            "data": json.loads((FIXTURES / f"{name}.json").read_text()),
        }
        for name in VALID_FIXTURES
    ]
    wire_invalid: list[dict[str, object]] = json.loads(
        (FIXTURES / "wire_invalid_cases.json").read_text()
    )
    cases.extend(wire_invalid)
    return cases


CASES = _all_cases()


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c["name"]))
def test_pydantic_verdict_matches_the_fixture(case: dict[str, object]) -> None:
    """Half of the cross-language agreement test. The other half is the same
    fixture files read by Vitest in `web`, asserted against the generated Zod
    validator. Two halves, one set of files, one verdict per case — a codegen
    bug shows up as the two halves disagreeing."""
    try:
        Experience.model_validate(case["data"])
        accepted = True
    except ValidationError:
        accepted = False
    assert accepted is case["valid"]


def test_generated_schema_has_no_diff() -> None:
    """The gate rule, as a test. Runs the generator in --check mode, which
    fails if what is committed differs from what Pydantic produces right now."""
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        pytest.skip("pnpm not on PATH; the same check runs in web's gate and in CI")
    result = subprocess.run(  # noqa: S603  # fixed argv, resolved binary, no shell
        [pnpm, "--silent", "schema:check"],
        cwd=API.parent / "web",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
