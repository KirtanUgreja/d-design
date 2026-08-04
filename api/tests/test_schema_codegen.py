"""The two tests that only exist because of the language split.

Both are cheap, and between them they are the whole reason "one source of
truth" survives a language boundary (docs/coderules/python.md -> "Test").
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from schema import Probe

API = Path(__file__).resolve().parent.parent
CASES = json.loads((API / "tests" / "fixtures" / "probe_cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c["name"]))
def test_pydantic_verdict_matches_the_fixture(case: dict[str, object]) -> None:
    """Half of the cross-language agreement test. The other half is the same
    fixture file read by Vitest in `web`, asserted against the generated Zod
    validator. Two halves, one file, one verdict per case — a codegen bug shows
    up as the two halves disagreeing."""
    try:
        Probe.model_validate(case["data"])
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
