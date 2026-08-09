"""The migration's only real assertion, and its Python half.

*"A format migration that changes a pixel has changed a design."* The two
system art directions were hand-transcribed from TypeScript constants into
`features/art_direction/seed.py`; there is no automated path between the two
languages, so the transcription is checked rather than trusted.

The check is one fixture with a test on each side — the pattern this repo
already uses for a cross-language invariant (`test_visual_seed.py` and
`renderer.test.ts` agreeing on FNV-1a, `schema/fixtures/*.json` and
`schema.test.ts` agreeing on validation verdicts).

  * This file: the fixture is exactly what `seed.py` produces, and what it
    produces parses, round-trips through DTCG, and satisfies the format's own
    rules about what lives where.
  * `web/src/features/art-direction/art-direction.test.ts`: the fixture,
    through `fromRecord` and `toCssVars`, emits a CSS-variable map identical to
    the v1 constant's. That is the half that actually says "no pixel moved".

Neither half is sufficient alone, which is why the fixture is checked in rather
than generated during the test. A fixture built by the code under test agrees
with itself.
"""

import json

import pytest

from features.art_direction.dtcg import from_document, to_document
from features.art_direction.seed import FIXTURE, SYSTEM_ART_DIRECTIONS, wire_payload
from lib.result import Ok
from schema.art_direction import EXTENSION_KEY, ArtDirectionRecord

_FIXTURE_DATA: list[dict[str, object]] = json.loads(FIXTURE.read_text())


def test_the_fixture_is_what_the_seed_produces() -> None:
    """The drift-catcher. Edit `seed.py` without re-running
    `uv run python -m scripts.export_art_directions` and this fails — which is
    the same failure mode, and the same fix, as the schema codegen's
    `--check`."""
    assert _FIXTURE_DATA == wire_payload(), (
        "art-direction fixture is stale; run "
        "`uv run python -m scripts.export_art_directions`"
    )


def test_the_fixture_parses_back_into_records() -> None:
    """What `web` and `render` do with it, done here first. A fixture that only
    this language can read is not a contract."""
    parsed = [ArtDirectionRecord.model_validate(item) for item in _FIXTURE_DATA]
    assert [record.id for record in parsed] == [
        record.id for record in SYSTEM_ART_DIRECTIONS
    ]


@pytest.mark.parametrize("record", SYSTEM_ART_DIRECTIONS, ids=lambda r: r.id)
def test_the_dtcg_document_round_trips(record: ArtDirectionRecord) -> None:
    """An interchange format nobody reads back is a claim rather than a
    format."""
    document = to_document(record)
    restored = from_document(document)
    assert isinstance(restored, Ok), restored
    assert restored.value == record


@pytest.mark.parametrize("record", SYSTEM_ART_DIRECTIONS, ids=lambda r: r.id)
def test_the_document_puts_everything_non_standard_under_one_extension_key(
    record: ArtDirectionRecord,
) -> None:
    """The format's central split, asserted rather than described.

    Budgets, brand mapping, default motion and every fluid length live under
    one reverse-domain key; the rest of the document is DTCG groups, and each
    of their leaves carries a `$type` and a `$value`. A leaf that gained a
    presentational value with no `$type` would be a token this format cannot
    say anything about, which is how a `styleOverride` field arrives without
    anyone naming it one.
    """
    document = to_document(record)
    extensions = document["$extensions"]
    assert isinstance(extensions, dict)
    assert list(extensions) == [EXTENSION_KEY]

    payload_keys = extensions[EXTENSION_KEY]
    assert isinstance(payload_keys, dict)
    for key in ("budgets", "brandMapping", "defaultMotion", "fluid"):
        assert key in payload_keys

    for group_name, group in document.items():
        if group_name == "$extensions":
            continue
        for path, leaf in _leaves(group):
            assert "$type" in leaf and "$value" in leaf, f"{group_name}.{path}"


@pytest.mark.parametrize("record", SYSTEM_ART_DIRECTIONS, ids=lambda r: r.id)
def test_no_dtcg_dimension_carries_a_unit_the_spec_forbids(
    record: ArtDirectionRecord,
) -> None:
    """`px` and `rem`, and nothing else — the finding that reshaped this phase.

    The type already forbids it, so this asserts the *split* rather than the
    field: a fluid length that got promoted into the DTCG layer by a
    well-meaning refactor would fail here even if it happened to be expressible,
    because the emitted document is what a designer's tool would read.
    """
    document = to_document(record)
    for group_name, group in document.items():
        if group_name == "$extensions":
            continue
        for path, leaf in _leaves(group):
            if leaf.get("$type") != "dimension":
                continue
            value = leaf["$value"]
            assert isinstance(value, dict)
            assert value["unit"] in ("px", "rem"), f"{group_name}.{path}"


def test_the_migrated_art_directions_keep_the_v1_character_caps() -> None:
    """Phase 01 carried the v1 caps across unchanged, and phase 04 is the first
    divergence — which the previous version of this test named as its own end
    date rather than being surprised by.

    The assertion is still worth having and is now the more interesting one. It
    was "all budgets are equal", which was a statement about a migration; it is
    now "the two directions that were *migrated* are still equal, and the one
    that was authored is not". The first half is what stops a later edit
    smuggling a behaviour change into the two records whose whole promise was
    that nothing moved. The second half is what stops `ContentBudgets` quietly
    reverting to a product-wide constant — which is what it was in v1, and what
    docs/v2/art-direction-system.md calls the honest crack in the thesis.
    """
    migrated = [
        record.extensions.budgets
        for record in SYSTEM_ART_DIRECTIONS
        if record.id in ("cinematic-dark", "editorial-light")
    ]
    assert len(migrated) == 2
    assert migrated[0] == migrated[1]

    brutalist = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == "bold-brutalist")
    assert brutalist.extensions.budgets != migrated[0]
    # 34, and the specific number matters: it is what pays for a hero running
    # 13x body size (`HEADLINE_SET_WIDTH` in lint.py). A budget loosened here
    # without the type scale coming down fails the linter, which is the coupling
    # being enforced rather than described.
    assert brutalist.extensions.budgets.headline == 34


def _leaves(node: object, prefix: str = "") -> list[tuple[str, dict[str, object]]]:
    """Every `$value`-bearing leaf under a DTCG group, with its path.

    A leaf is a dict carrying `$value`; anything else that is a dict is a
    group. That is the spec's own rule for telling the two apart, and using it
    here rather than a hardcoded depth is what lets the assertions above stay
    true when a group is added.
    """
    if not isinstance(node, dict):
        return []
    if "$value" in node:
        return [(prefix, node)]
    found: list[tuple[str, dict[str, object]]] = []
    for key, child in node.items():
        found.extend(_leaves(child, f"{prefix}.{key}" if prefix else key))
    return found
