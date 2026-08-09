"""A motion vocabulary — the fifth token group, and the one that is its own axis.

docs/v2/art-direction-system.md -> "Motion as an independent axis", and
docs/v2/plan/02-motion-axis.md. Pydantic owns it for the same reason it owns
`ArtDirectionRecord`: the record crosses the language boundary, so the Zod
validator and the TypeScript types are generated from here.

## Why this is a separate table from the art direction

Motion travelled *with* an art direction in v1 — `resolveArtDirection` paired
one vocabulary to each in a code table, so choosing a look chose the motion with
it. That was right while there was one art direction and defensible while there
were two. It stops being right at three: 3 art directions x 4 vocabularies is
twelve combinations from seven authored artifacts, and that ratio is the whole
argument for decoupling them.

The art direction still names a `defaultMotion`, so the surface stays curated —
someone who picks a look gets a coherent pairing without choosing twice. It is
a *default*, applied when an experience is created, and never a resolution step:
an experience carries its own reference from that moment on, which is what makes
a reskin unable to silently discard a motion choice.

## The shape is the spec's, with one field the spec's sketch is missing

`docs/v2/art-direction-system.md` gives the shape, and transcribing v1's two
vocabularies into it found a gap: **there is nowhere to put `emphasize`'s scale
factor.** It is 0.96 under `cinematic-slow` and 0.99 under `editorial-restrained`
— "a stage swells, a printed page does not" — and dropping it would have made
the migration change a design. So `distances` carries `emphasize_scale`
alongside the two lengths, which is where a "how far does it travel" number
belongs even though the travel is a scale rather than a translate.

Nothing else in v1's data is lost. `parallax` and `none` have no durations of
their own — parallax is scroll-linked and `none` is off — so the spec's two
durations are the two that exist, and the runtime record the renderer reads is
built back out on the TypeScript side (`from-motion-record.ts`).

## Why the renderer's shape is not this shape

The renderer indexes a vocabulary by intent: `vocabulary.intents[block.motion]`.
This record is authored per *concept* — one ease, two durations, two distances —
because that is how the values are actually decided, and because an authoring
form with four near-identical intent blocks invites four inconsistent answers to
one question. The mapping between them lives in exactly one place and the
renderer is untouched by this phase, which rule 6 requires: a fifth intent here
would be a renderer change, and the schema's `Block.motion` union of four is the
contract.
"""

from typing import Annotated

from pydantic import Field

from schema.base import Schema

# A cubic-bezier as four numbers, never a string. The same standard the art
# direction's tokens are held to — "a token whose type is 'any string' is a
# token that will have to be redesigned" — and here it is also a safety
# property: an easing string is echoed into a stylesheet.
#
# The x components of a CSS cubic-bezier are bounded to 0-1 and the y components
# deliberately are not: an overshoot curve (`physics-playful`, phase 11) needs
# y > 1, and a range that forbade it would forbid the vocabulary.
Easing = Annotated[
    list[float],
    Field(min_length=4, max_length=4),
]


class MotionDurations(Schema):
    """The two intents that have a duration.

    `parallax` is scroll-linked, so its "duration" is however long the reader
    scrolls; `none` is off. Neither is a number anybody authors, and giving them
    fields would invite someone to fill them in.
    """

    reveal: int = Field(ge=0, le=5000)
    emphasize: int = Field(ge=0, le=5000)


class MotionDistances(Schema):
    """How far a thing travels, in the three senses this vocabulary has one."""

    reveal_y: int = Field(ge=0, le=200)
    # The clamp bound on scroll-linked travel, not a fixed offset: the wrapper
    # computes the offset per frame and this is how far it may go.
    parallax_factor: int = Field(ge=0, le=400)
    # The gap in the spec's sketch, found by transcribing v1. `emphasize` scales
    # *up from* this value, so it is a distance in the only sense that intent
    # has one. 1.0 is no scaling, which is what a vocabulary with no swell says.
    emphasize_scale: float = Field(gt=0, le=1)


class SlidesVariant(Schema):
    """The same vocabulary, timed for a deck.

    Phase 10 reads this and nothing else does. Authoring it now costs two
    numbers per vocabulary and is what stops phase 10 inventing a second timing
    system — which is the way slides mode becomes a code path instead of a
    lookup.

    There is no `trigger` field. In slides mode motion fires on *advance*, which
    is not a viewport fraction and not a number: it is a different event, and a
    field whose only legal value is the string `'advance'` would be a constant
    wearing a token's clothes.
    """

    durations: MotionDurations


class ReducedMotion(Schema):
    """The accessibility floor, declared per vocabulary rather than globally.

    A duration and nothing else, because everything else is fixed by what
    reduced motion *means*: opacity only, no transform, no parallax. Those are
    not per-vocabulary choices and the format gives nobody a place to make them
    — which is the difference between a floor and a default.

    v1 had one global constant and that was correct with one vocabulary. It
    stops being correct with four: 200ms under `mechanical-snap` and 200ms under
    `physics-playful` are not the same design even when both are a bare fade.

    Capped at 300ms. WCAG 2.3.3 and docs/v1/art-direction.md treat this as a
    design requirement rather than a checkbox, and a "reduced" mode slower than
    a third of a second is a vocabulary arguing with the request.
    """

    duration: int = Field(ge=0, le=300)


class MotionVocabularyRecord(Schema):
    """One version of one vocabulary. `(id, version)`, matching the primary key
    in migration 0008.

    No `owner_id` anywhere near this, and `motion_vocabularies` has no such
    column: user-authored motion is not a v2 feature, and a nullable column with
    only ever one value in it teaches the next reader the wrong thing. It gains
    one when it needs one, which is a migration and a policy change together.
    """

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9-]*$")
    version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    ease: Easing
    # A second curve, for `emphasize` only. Two rather than one because a swell
    # and a rise are different gestures — v1 authored them separately and the
    # difference is audible when you watch them.
    ease_emphasis: Easing
    durations: MotionDurations
    distances: MotionDistances
    stagger: int = Field(ge=0, le=500)
    # Siblings after which stagger stops accumulating. A constant in v1
    # (`MAX_STAGGER_SIBLINGS = 5`); a field here because "how long a sequence
    # reads as one movement" is a property of the vocabulary, and a nine-item
    # list under a 120ms stagger is a second of dead time either way.
    stagger_cap: int = Field(ge=0, le=20)
    # Viewport fraction that must be visible before motion fires. Short motion
    # that starts while a block is barely on screen has finished before anyone
    # is looking at it, which is why this is a token and not 0.25 everywhere.
    trigger: float = Field(ge=0, le=1)
    slides_variant: SlidesVariant
    reduced_motion: ReducedMotion


class MotionVocabularyRef(Schema):
    """What an experience stores.

    An id with no version, deliberately, and the asymmetry with
    `ArtDirectionRef` is the point rather than an oversight. An art direction is
    user-editable from late v2, so a reference to one has to say *which*
    version or a published page restyles itself when its author edits it. Motion
    vocabularies are system rows with no `owner_id` column to make them
    otherwise: a new version is a migration, deliberate and reviewed, and the
    published artifact freezes the resolved vocabulary anyway.

    A model rather than a bare `str` so the asymmetry is visible at every call
    site instead of being a `str` nobody looks twice at — and so adding a
    version later is a field rather than a type change with a blast radius.
    """

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9-]*$")
