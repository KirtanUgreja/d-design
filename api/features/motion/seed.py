"""The two system motion vocabularies, transcribed from v1's constants.

`CINEMATIC_MOTION` becomes `cinematic-slow` v1 and `EDITORIAL_MOTION` becomes
`editorial-restrained` v1. **Same numbers.** The renames are the spec's names
(docs/v2/art-direction-system.md), and a rename is all they are — a phase that
also retuned the motion would be two changes wearing one commit message, and
the equality proof in `api/tests/test_motion_seed.py` exists to make that
impossible to do by accident.

Two vocabularies, not four. `mechanical-snap` and `physics-playful` are phase
[11](../../../docs/v2/plan/11-range.md), because authoring them here would be
authoring motion for art directions that do not exist yet — the exact mistake
the build order is arranged to avoid.

The only genuinely new numbers are `slides_variant` and `reduced_motion`, and
each is annotated below with what it was derived from rather than left as a
number someone will later assume was measured.
"""

from pathlib import Path

from schema.motion import (
    MotionDistances,
    MotionDurations,
    MotionVocabularyRecord,
    ReducedMotion,
    SlidesVariant,
)

# v1's `EXPO_OUT` and `EASE_EMPHASIS`, and `EASE_EDITORIAL`. Named here rather
# than inlined for the same reason they were named there: a bezier is four
# magic numbers, and the name is the only thing that says which gesture it is.
_EXPO_OUT = [0.16, 1.0, 0.3, 1.0]
_EASE_EMPHASIS = [0.22, 1.0, 0.36, 1.0]
_EASE_EDITORIAL = [0.32, 0.72, 0.0, 1.0]

# v1's `MAX_STAGGER_SIBLINGS`, which was a module constant shared by both
# vocabularies. It becomes a field with the same value in both — the phase's
# rule that a migration changes no behaviour applies to constants that became
# fields just as much as to values.
_V1_STAGGER_CAP = 5

# v1's one global `REDUCED_MOTION` used 200ms for every intent. Both
# vocabularies declare it, so the timing is unchanged; what *does* change is
# that each now fades on its own easing curve and fires at its own trigger,
# because those are properties of the vocabulary rather than of the floor.
# `editorial-restrained` is the one that moves, and it moves toward being
# itself.
_V1_REDUCED_DURATION = 200


CINEMATIC_SLOW = MotionVocabularyRecord(
    id="cinematic-slow",
    version=1,
    name="Cinematic Slow",
    ease=_EXPO_OUT,
    ease_emphasis=_EASE_EMPHASIS,
    durations=MotionDurations(reveal=900, emphasize=1100),
    distances=MotionDistances(
        reveal_y=32,
        parallax_factor=80,
        emphasize_scale=0.96,
    ),
    stagger=120,
    stagger_cap=_V1_STAGGER_CAP,
    trigger=0.25,
    # Roughly two-thirds of the scroll timings. A slide advance is a deliberate
    # act with a person waiting on it, where a scroll reveal is something you
    # arrive at — the same gesture has to resolve sooner when someone pressed a
    # key to ask for it. Not measured; the first thing phase 10 should look at.
    slides_variant=SlidesVariant(durations=MotionDurations(reveal=600, emphasize=700)),
    reduced_motion=ReducedMotion(duration=_V1_REDUCED_DURATION),
)


EDITORIAL_RESTRAINED = MotionVocabularyRecord(
    id="editorial-restrained",
    version=1,
    name="Editorial Restrained",
    ease=_EASE_EDITORIAL,
    # One curve for both gestures, which is itself the design: this vocabulary
    # is motion you notice only if you look, and two easings would be two things
    # to notice.
    ease_emphasis=_EASE_EDITORIAL,
    durations=MotionDurations(reveal=320, emphasize=360),
    distances=MotionDistances(
        reveal_y=12,
        # Real but small. Zero would be a lie the token layer should not tell,
        # since the schema still lets a scene ask for parallax.
        parallax_factor=24,
        # Barely a swell. A printed page does not.
        emphasize_scale=0.99,
    ),
    stagger=40,
    stagger_cap=_V1_STAGGER_CAP,
    # Later than cinematic-slow's 0.25: short motion that starts while a block
    # is barely on screen has finished before anyone is looking at it.
    trigger=0.4,
    slides_variant=SlidesVariant(durations=MotionDurations(reveal=220, emphasize=240)),
    reduced_motion=ReducedMotion(duration=_V1_REDUCED_DURATION),
)


SYSTEM_MOTION_VOCABULARIES: tuple[MotionVocabularyRecord, ...] = (
    CINEMATIC_SLOW,
    EDITORIAL_RESTRAINED,
)


_FIXTURE_NAME = "motion_vocabularies.json"

# The wire form, and where it is checked in. Same arrangement as the art
# directions' fixture and for the same reason: `web`'s tests and its `/dev/*`
# harnesses need these records without a database, and a fixture that only one
# language can read is not a contract.
FIXTURE = Path(__file__).resolve().parents[2] / "schema" / "fixtures" / _FIXTURE_NAME


def wire_payload() -> list[dict[str, object]]:
    return [
        record.model_dump(mode="json", by_alias=True)
        for record in SYSTEM_MOTION_VOCABULARIES
    ]
