"""The motion half of "a migration changes no behaviour".

Same arrangement as `test_art_direction_seed.py`, and the same reasoning: the
two vocabularies were hand-transcribed from TypeScript constants, there is no
automated path between the languages, so the transcription is checked rather
than trusted.

  * This file: the fixture is exactly what `seed.py` produces, and what it
    produces satisfies the rules the format is supposed to guarantee.
  * `web/src/features/art-direction/art-direction.test.ts`: the same fixture,
    through `fromMotionRecord`, produces the objects v1's constants held. That
    is the half that says the rename changed no timing.

The fixture is checked in rather than generated during the test, because a
fixture built by the code under test agrees with itself.
"""

import json

import pytest

from features.art_direction.seed import SYSTEM_ART_DIRECTIONS
from features.motion.seed import FIXTURE, SYSTEM_MOTION_VOCABULARIES, wire_payload
from schema.motion import MotionVocabularyRecord

_FIXTURE_DATA: list[dict[str, object]] = json.loads(FIXTURE.read_text())


def test_the_fixture_is_what_the_seed_produces() -> None:
    """Edit `seed.py` without re-running `uv run python -m scripts.export_motion`
    and this fails — the same failure mode, and the same fix, as the schema
    codegen's `--check`."""
    assert _FIXTURE_DATA == wire_payload(), (
        "motion fixture is stale; run `uv run python -m scripts.export_motion`"
    )


def test_the_fixture_parses_back_into_records() -> None:
    parsed = [MotionVocabularyRecord.model_validate(item) for item in _FIXTURE_DATA]
    assert [record.id for record in parsed] == [
        record.id for record in SYSTEM_MOTION_VOCABULARIES
    ]


def test_every_art_direction_defaults_to_a_vocabulary_that_exists() -> None:
    """The constraint the database does not have.

    `art_directions.default_motion` is text pointing at a row in a different
    table, with no foreign key behind it — the tables are seeded by two
    migrations and a rename in one without the other is the exact mistake that
    ships an experience whose motion cannot resolve. This is what stands in for
    the constraint, and it runs on every commit rather than on every deploy.
    """
    known = {record.id for record in SYSTEM_MOTION_VOCABULARIES}
    for art_direction in SYSTEM_ART_DIRECTIONS:
        assert art_direction.extensions.default_motion in known, art_direction.id


@pytest.mark.parametrize("record", SYSTEM_MOTION_VOCABULARIES, ids=lambda r: str(r.id))
def test_reduced_motion_is_a_floor_rather_than_a_choice(
    record: MotionVocabularyRecord,
) -> None:
    """The format gives a vocabulary one number and no way to declare a reduced
    mode that moves — the difference between a floor and a default.

    Asserted here as well as in TypeScript because the two halves check
    different things: this one says the *format* cannot express a louder floor,
    and `art-direction.test.ts` says the mapping does not build one anyway.
    """
    assert 0 <= record.reduced_motion.duration <= 300
    assert set(record.reduced_motion.model_dump()) == {"duration"}


@pytest.mark.parametrize("record", SYSTEM_MOTION_VOCABULARIES, ids=lambda r: str(r.id))
def test_every_vocabulary_declares_a_slides_variant(
    record: MotionVocabularyRecord,
) -> None:
    """Phase 10 reads it and nothing else does, which is exactly why it is worth
    asserting now: an unread field is one nobody notices the absence of until
    the phase that needs it is halfway built.

    Faster than the scroll timings, both intents. A slide advance is a
    deliberate act with a person waiting on it; a scroll reveal is something you
    arrive at.
    """
    assert record.slides_variant.durations.reveal <= record.durations.reveal
    assert record.slides_variant.durations.emphasize <= record.durations.emphasize


def test_the_two_vocabularies_are_materially_different() -> None:
    """Not a threshold on how different — that would be a taste assertion — just
    that neither was copied. Two vocabularies that time the same are one
    vocabulary and a rename."""
    slow, restrained = SYSTEM_MOTION_VOCABULARIES
    assert restrained.durations != slow.durations
    assert restrained.distances != slow.distances
    assert restrained.stagger != slow.stagger
