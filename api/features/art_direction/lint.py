"""The AD linter. One validator, two purposes.

It refuses art directions that are unreadable, and it refuses art directions
that are an injection. **Building it as one thing is what stops the security
half being deferred as separate work** (docs/v2/plan/03-ad-linter.md), and it is
why `check_grammar` is called from inside this module rather than sitting beside
it as something a caller might forget.

## It runs in `api`, at the point of save

The linter stands between a user-authored token value and a published page, so
it runs where the write happens. `web` may run the same rules for live feedback
as someone types; it may not be the only place they run.

Today the write is `from_document` — the DTCG import boundary — and the seeds,
which `test_lint.py` asserts pass. When user authoring ships it gains a save
route, and that route calls this function. The rule the phase states is "an AD
saved by a route that skips the linter is impossible", and the way that stays
true is that there is one save path.

## Every rule is a hard failure

There is no severity on `LintFinding` and no warning tier to demote a rule into.
An art direction that fails cannot be saved — the same philosophy as scene
validation, which makes bad output unrepresentable rather than asking nicely.

Every bound has a reason, and the reasons are in the messages rather than in a
table somewhere else. `hero/normal < 2.5` produces a design with no hierarchy;
`> 8` produces a headline with orphaned body text. These are not taste — they
are the range outside which the renderer produces something nobody would defend.

## Fails closed on its own exception

`lint_art_direction` catches everything. A linter that raises and is caught by a
caller returning "no findings" is a vulnerability, not error handling
(docs/coderules/README.md rule 10) — so the catch lives here, where the only
thing it can turn into is a finding.
"""

from itertools import pairwise

from features.art_direction.lint_contrast import (
    Rgb,
    apca_lc,
    contrast_ratio,
    to_oklch,
    to_rgb,
)
from features.art_direction.lint_grammar import check_grammar
from schema.art_direction import (
    ArtDirectionRecord,
    ColorRole,
    DtcgColorToken,
    LintFinding,
    LintReport,
)
from schema.motion import MotionVocabularyRecord

# ---------------------------------------------------------------------------
# Bounds. Every one of them is in docs/v2/plan/03-ad-linter.md's table; the
# reasons live in the messages, next to the rule that uses them.
# ---------------------------------------------------------------------------

_WCAG_BODY = 4.5
_WCAG_LARGE = 3.0
_APCA_BODY = 75.0
_APCA_LARGE = 60.0

# Which roles are set large enough to be judged as display type. Derived from
# the roles rather than from the numbers, because the numbers are clamp triples
# in mixed units and "is this large text" is a question about the design's
# intent for the role, not about one viewport width.
#
# **`eyebrow` is deliberately in the body set, not the incidental one.** The
# phase's table offers `Lc 45` for "incidental/disabled", and an eyebrow is
# neither: it is content a reader is meant to read, and it is the *smallest*
# text in the system. APCA's own model asks for more contrast as text gets
# smaller, so giving the smallest role the loosest threshold would invert the
# standard being applied. It is judged as body, which is already generous.
_LARGE_ROLES = frozenset({"hero", "section", "stat"})

# Line height matters for text that wraps. `hero`, `section`, `stat` and
# `eyebrow` are single-line by design — a headline that wraps to two lines wants
# the tight leading, and an eyebrow is a label — so they get the display floor
# and the prose roles get the readability band.
_PROSE_ROLES = ("lead", "normal", "muted")
_DISPLAY_LEADING_MIN = 0.85
_PROSE_LEADING_MIN, _PROSE_LEADING_MAX = 1.4, 1.8

# The floor is about perceptible hierarchy and has nothing to do with how long
# a headline is, so it is a plain ratio and phase 04 did not move it.
#
# **The ceiling was 8.0 and it was wrong, and art direction #3 is what showed
# it.** `bold-brutalist` runs hero at 13.18x body, which the flat ceiling
# rejected — and the rejection was the rule mistaking a value it had only ever
# seen under two art directions for a universal one (the exact failure
# docs/v2/plan/README.md predicts under "the values a system holds globally").
#
# What the ceiling was actually protecting against is in its own message: a
# headline that *orphans the body text under it*. That is not a property of the
# ratio. It is a property of how much text is set at that size — 60 characters
# at 8x is a wall, 34 characters at 13x is a poster — so the honest bound is on
# the product of the two, and `_HEADLINE_SET_WIDTH_MAX` below is it.
#
# The ratio keeps an absolute ceiling as a backstop, because the product alone
# would let a 20-character budget buy hero at 26x body.
_SCALE_RATIO_MIN, _SCALE_RATIO_MAX = 2.5, 14.0

# Roughly, a headline's set width at full size measured in body-text ems:
# characters x how many times body size the hero is. It is a physical quantity,
# which is why it is a better bound than either factor alone.
#
# **The three art directions landed at 270, 452 and 448 without being tuned to
# it**, and two of those were authored before this rule existed. A constant that
# three independently-authored designs agree on is the kind of thing only a
# third data point can show you; with two, "global" and "cinematic-dark's" are
# indistinguishable.
#
# 520 leaves ~15% over the loudest of the three. Note it is *stricter* than the
# flat 8.0 in a case that one waved through: 8x body against the 80-character
# budget docs/v2/art-direction-system.md sketches for `editorial-light` is 640,
# and is now refused. This rule is not the old one relaxed to admit a
# fashionable art direction.
_HEADLINE_SET_WIDTH_MAX = 520.0
_MEASURE_MIN_CH, _MEASURE_MAX_CH = 45.0, 80.0
_SPACE_RATIO_MIN, _SPACE_RATIO_MAX = 1.2, 2.0
_HEADLINE_BUDGET_MIN, _HEADLINE_BUDGET_MAX = 20, 120

_DURATION_MIN_MS, _DURATION_MAX_MS = 120, 1400
_REDUCED_MAX_MS = 300

# Rule 19's saturation bound. A colour that is simultaneously loud and light,
# sitting on a near-black ground, blooms — which is the effect the no-gradient
# rules forbid by every other route, arriving through the palette instead.
_OKLCH_CHROMA_MAX = 0.20
_OKLCH_LIGHTNESS_MAX = 0.72
_DARK_GROUND_LIGHTNESS = 0.30

# The order the type scale must descend in. `normal >= muted` rather than `>`
# because they are the same size in both shipped directions and differ by
# colour, which is a legitimate design.
_SCALE_ORDER = ("hero", "section", "lead", "normal", "muted", "eyebrow")

_ROLES = ("hero", "section", "lead", "normal", "muted", "eyebrow", "stat")


def lint_art_direction(record: ArtDirectionRecord) -> LintReport:
    """Every rule, in one pass, with an unexpected exception as a finding.

    The `except Exception` is the point rather than a safety net: rule 10 says
    anything that grants fails closed, and a linter is a thing that grants. A
    crash that produced an empty report would be a save allowed *because* the
    check broke.
    """
    try:
        findings: list[LintFinding] = []
        findings.extend(check_grammar(record))
        findings.extend(_check_contrast(record))
        findings.extend(_check_saturation(record))
        findings.extend(_check_type_scale(record))
        findings.extend(_check_rhythm(record))
        findings.extend(_check_budgets(record))
        findings.extend(_check_brand_mapping(record))
        findings.extend(_check_no_ramp_or_bloom(record))
        return LintReport(findings=findings)
    except Exception as e:
        return LintReport(
            findings=[
                LintFinding(
                    rule="LINTER_ERROR",
                    path="(record)",
                    message=(
                        f"the linter raised {type(e).__name__} and could not finish. "
                        "The art direction is refused rather than allowed, because a "
                        "check that failed to run is not a check that passed."
                    ),
                )
            ]
        )


def lint_art_direction_with_brand(
    record: ArtDirectionRecord, brand_primary: str
) -> LintReport:
    """The second thing that has to be lintable, and phase 04 is what found it.

    **An art direction is lintable on its own; an art direction plus a brand is
    a different object that must also be lintable.** For the two v1 directions
    the distinction was invisible — a brand lands on `accent`, and `resolveBrand`
    corrects it until it clears both gates, so the ground the rules run against
    is the authored one either way. `bold-brutalist` sets `accent_role='bg'` and
    takes the brand *as the ground, uncorrected*, which means every contrast pair
    in the art direction is measured against a colour that does not exist until
    a customer attaches a kit.

    Nothing is corrected here and nothing could be: correcting the ground is the
    one thing this art direction exists not to do. What this does is refuse, at
    the point the kit is chosen, with a message written for the person who chose
    the colour. `web/src/features/art-direction/resolve-brand.ts` runs the same
    two pairs at render time, because a stored brand kit can predate a change to
    the art direction it is applied to.

    Returns an empty report for an art direction that does not take a brand
    ground — not because there is nothing to check, but because for those the
    check is `resolveBrand`'s correction loop and it happens in `web`, where the
    measurement has to be synchronous and local (rule 6).
    """
    try:
        mapping = record.extensions.brand_mapping
        if mapping.accent_role != "bg":
            return LintReport(findings=[])

        parsed = _parse_hex(brand_primary)
        if parsed is None:
            return LintReport(
                findings=[
                    LintFinding(
                        rule="BRAND_PRIMARY_NOT_A_COLOUR",
                        path="brand.primary",
                        message=(
                            "is not a six-digit hex colour. It is parsed and "
                            "re-serialized rather than passed through, because this "
                            "value becomes a CSS custom property on a published page."
                        ),
                    )
                ]
            )

        findings: list[LintFinding] = []
        findings.extend(
            _judge(
                text=to_rgb(record.tokens.color.ink.value),
                ground=parsed,
                large=False,
                path="brand.primary",
                what=f"{record.id}'s body text on the brand colour as the page ground",
            )
        )
        # The pair that is easy to forget and matters most: a CTA label is
        # `bg`-coloured text, so when `bg` becomes the brand the most important
        # text on the page changes colour and lands on a fill nobody
        # re-measured it against.
        findings.extend(
            _judge(
                text=parsed,
                ground=to_rgb(record.tokens.color.accent.value),
                large=False,
                path="brand.primary",
                what=f"the brand colour as a CTA label on {record.id}'s button fill",
            )
        )
        return LintReport(findings=findings)
    except Exception as e:
        return LintReport(
            findings=[
                LintFinding(
                    rule="LINTER_ERROR",
                    path="brand.primary",
                    message=(
                        f"the linter raised {type(e).__name__} and could not finish. "
                        "The brand kit is refused rather than allowed."
                    ),
                )
            ]
        )


def _parse_hex(value: str) -> Rgb | None:
    """`#rrggbb` only. The one parse, and it returns `None` rather than raising
    because a malformed brand colour is a user typing, not a bug."""
    text = value.strip()
    if len(text) != 7 or not text.startswith("#"):
        return None
    try:
        channels = [float(int(text[i : i + 2], 16)) for i in (1, 3, 5)]
    except ValueError:
        return None
    return Rgb(channels[0], channels[1], channels[2], 1.0)


def lint_motion_vocabulary(record: MotionVocabularyRecord) -> LintReport:
    """The motion half of the rules table.

    A separate entry point because motion is a separate axis since phase 02 and
    the two are saved separately — folding it into `lint_art_direction` would be
    the code table growing back in the validator.
    """
    try:
        findings: list[LintFinding] = []
        for name, value in (
            ("durations.reveal", record.durations.reveal),
            ("durations.emphasize", record.durations.emphasize),
            ("slidesVariant.durations.reveal", record.slides_variant.durations.reveal),
            (
                "slidesVariant.durations.emphasize",
                record.slides_variant.durations.emphasize,
            ),
        ):
            if not _DURATION_MIN_MS <= value <= _DURATION_MAX_MS:
                findings.append(
                    LintFinding(
                        rule="MOTION_DURATION_OUT_OF_RANGE",
                        path=name,
                        message=(
                            f"{value}ms is outside {_DURATION_MIN_MS}-"
                            f"{_DURATION_MAX_MS}ms. Below the floor the motion reads "
                            "as a jump rather than a movement; above the ceiling the "
                            "reader has finished with the scene before it finishes "
                            "arriving."
                        ),
                    )
                )

        if record.reduced_motion.duration > _REDUCED_MAX_MS:
            findings.append(
                LintFinding(
                    rule="REDUCED_MOTION_TOO_SLOW",
                    path="reducedMotion.duration",
                    message=(
                        f"{record.reduced_motion.duration}ms exceeds "
                        f"{_REDUCED_MAX_MS}ms. A reduced mode slower than a third of "
                        "a second is a vocabulary arguing with the request."
                    ),
                )
            )
        return LintReport(findings=findings)
    except Exception as e:
        return LintReport(
            findings=[
                LintFinding(
                    rule="LINTER_ERROR",
                    path="(record)",
                    message=f"the linter raised {type(e).__name__} and could not finish.",
                )
            ]
        )


# ---------------------------------------------------------------------------
# Contrast
# ---------------------------------------------------------------------------


def _palette_token(record: ArtDirectionRecord, role: ColorRole) -> DtcgColorToken:
    """A palette role by its wire name. The fluid type scale names colours in
    camelCase because that is what the renderer reads; the palette model uses
    Python's own spelling."""
    attribute = "".join("_" + char.lower() if char.isupper() else char for char in role)
    token = getattr(record.tokens.color, attribute)
    if not isinstance(token, DtcgColorToken):
        # Unreachable through the model, and a raise rather than a finding: a
        # palette that does not hold colour tokens is a bug in this process, not
        # an art direction that failed. `lint_art_direction` catches it and
        # refuses the save anyway, which is the fail-closed path doing its job.
        raise TypeError(f"palette role {role!r} is not a colour token")
    return token


def _check_contrast(record: ArtDirectionRecord) -> list[LintFinding]:
    """Both standards, every text role, against every ground.

    **Two grounds, not one.** `bgElevated` is a real surface that real text sits
    on, and an art direction whose muted text passes on the page and fails on a
    framed panel has a bug that only appears in one layout. This is the
    buildable half of the phase-17 ground-cycle rule; the inverted-scene half
    arrives with the scenes that invert.

    **And the CTA.** Its label is `bg` on an `accent` fill — the most important
    text on the page, and the one pair no type role describes, because the
    colours are the other way round.
    """
    findings: list[LintFinding] = []
    fluid = record.extensions.fluid.type

    grounds = (
        ("bg", record.tokens.color.bg),
        ("bgElevated", record.tokens.color.bg_elevated),
    )

    for ground_name, ground_token in grounds:
        ground = to_rgb(ground_token.value)
        for role in _ROLES:
            role_config = getattr(fluid, role)
            color_role: ColorRole = role_config.color or "ink"
            text = to_rgb(_palette_token(record, color_role).value)
            findings.extend(
                _judge(
                    text=text,
                    ground=ground,
                    large=role in _LARGE_ROLES,
                    path=f"fluid.type.{role}",
                    what=f"{role} text ({color_role}) on {ground_name}",
                )
            )

    # The CTA fill. Not a type role, and the one pair that would be missed by
    # walking the type scale alone.
    findings.extend(
        _judge(
            text=to_rgb(record.tokens.color.bg.value),
            ground=to_rgb(record.tokens.color.accent.value),
            large=False,
            path="tokens.color.accent",
            what="CTA label (bg) on the accent fill",
        )
    )
    return findings


def _judge(
    *, text: Rgb, ground: Rgb, large: bool, path: str, what: str
) -> list[LintFinding]:
    """WCAG for the floor, APCA for whether it is actually readable.

    Both, always, and both hard. Running only WCAG 2 yields muddy dark themes
    that clear the audit; running only APCA yields a beautiful page that fails a
    customer's compliance review.
    """
    findings: list[LintFinding] = []

    ratio = contrast_ratio(text, ground)
    wcag_floor = _WCAG_LARGE if large else _WCAG_BODY
    if ratio < wcag_floor:
        findings.append(
            LintFinding(
                rule="CONTRAST_BELOW_WCAG_AA",
                path=path,
                message=(
                    f"{what} is {ratio:.2f}:1, below the {wcag_floor}:1 that WCAG 2.2 "
                    "AA requires. This is the legal floor an accessibility audit "
                    "measures, whatever anyone thinks of what it measures."
                ),
            )
        )

    lc = abs(apca_lc(text, ground))
    apca_floor = _APCA_LARGE if large else _APCA_BODY
    if lc < apca_floor:
        findings.append(
            LintFinding(
                rule="CONTRAST_BELOW_APCA",
                path=path,
                message=(
                    f"{what} is Lc {lc:.1f}, below the Lc {apca_floor:.0f} this size "
                    "needs. WCAG 2's ratio is polarity-blind and scores a dark ground "
                    "the same as a light one; APCA is what notices that this is "
                    "muddy. When the two disagree, this is the one telling you "
                    "something true — the fix is the art direction, not the gate."
                ),
            )
        )
    return findings


def _check_saturation(record: ArtDirectionRecord) -> list[LintFinding]:
    """docs/design/principles.md rule 19, as a bound rather than a warning.

    A colour that is loud (`C`), light (`L`) and sitting on a near-black ground
    blooms — the same effect the no-gradient rules forbid by every other route,
    arriving through the palette instead. OKLCH rather than HSL because HSL's
    lightness calls a saturated yellow and a saturated blue equally light, so a
    bound expressed in it either rejects usable blues or admits fluorescence.
    """
    ground = to_oklch(to_rgb(record.tokens.color.bg.value))
    if ground.lightness >= _DARK_GROUND_LIGHTNESS:
        return []

    findings: list[LintFinding] = []
    fluid = record.extensions.fluid.type
    carried: set[ColorRole] = {getattr(fluid, role).color or "ink" for role in _ROLES}
    carried.add("accent")

    for role in sorted(carried):
        color = to_oklch(to_rgb(_palette_token(record, role).value))
        if color.chroma > _OKLCH_CHROMA_MAX and color.lightness > _OKLCH_LIGHTNESS_MAX:
            findings.append(
                LintFinding(
                    rule="SATURATION_BLOOMS_ON_DARK_GROUND",
                    path=f"tokens.color.{role}",
                    message=(
                        f"is OKLCH C {color.chroma:.3f} at L {color.lightness:.3f} on a "
                        f"ground at L {ground.lightness:.3f}. A colour that loud and "
                        "that light on a near-black ground blooms, which is the effect "
                        "the no-gradient rules exist to prevent."
                    ),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Type, rhythm, budgets
# ---------------------------------------------------------------------------


def _check_type_scale(record: ArtDirectionRecord) -> list[LintFinding]:
    findings: list[LintFinding] = []
    fluid = record.extensions.fluid.type
    dtcg = record.tokens.type

    # Compared at the `max` of each clamp — the size the design is at full
    # width, which is the one every role expresses in the same unit and the one
    # the composition was judged at.
    sizes = {role: getattr(fluid, role).size.max for role in _SCALE_ORDER}
    units = {size.unit for size in sizes.values()}
    if len(units) > 1:
        findings.append(
            LintFinding(
                rule="TYPE_SCALE_MIXED_UNITS",
                path="fluid.type",
                message=(
                    f"the roles top out in {len(units)} different units, so the scale "
                    "cannot be ordered. A scale whose steps are not comparable is not "
                    "a scale."
                ),
            )
        )
    else:
        for larger, smaller in pairwise(_SCALE_ORDER):
            a, b = sizes[larger].value, sizes[smaller].value
            allowed_equal = (larger, smaller) == ("normal", "muted")
            if b > a or (b == a and not allowed_equal):
                findings.append(
                    LintFinding(
                        rule="TYPE_SCALE_NOT_MONOTONIC",
                        path=f"fluid.type.{smaller}",
                        message=(
                            f"{smaller} is not smaller than {larger} ({b} vs {a}). "
                            "The scale is the hierarchy; a step that does not descend "
                            "is a role the reader cannot rank."
                        ),
                    )
                )

        hero, normal = sizes["hero"].value, sizes["normal"].value
        if normal > 0:
            ratio = hero / normal
            if not _SCALE_RATIO_MIN <= ratio <= _SCALE_RATIO_MAX:
                findings.append(
                    LintFinding(
                        rule="TYPE_SCALE_RANGE",
                        path="fluid.type.hero",
                        message=(
                            f"hero is {ratio:.2f}x body, outside {_SCALE_RATIO_MIN}-"
                            f"{_SCALE_RATIO_MAX}. Below the floor the page has no "
                            "hierarchy; above the ceiling no character budget is "
                            "tight enough to make the headline set."
                        ),
                    )
                )

            # The bound that replaced the flat ceiling. A large ratio is not a
            # defect on its own — it is a defect unpaid for, and the headline
            # budget is what pays for it.
            budget = record.extensions.budgets.headline
            set_width = ratio * budget
            if set_width > _HEADLINE_SET_WIDTH_MAX:
                findings.append(
                    LintFinding(
                        rule="HEADLINE_SET_WIDTH",
                        path="budgets.headline",
                        message=(
                            f"{budget} characters at {ratio:.2f}x body sets a headline "
                            f"{set_width:.0f} body-ems wide, over the "
                            f"{_HEADLINE_SET_WIDTH_MAX:.0f} a page can carry without "
                            "the body text under it reading as a caption. Type this "
                            "large is allowed, and the budget is what pays for it: "
                            f"cut the headline budget to "
                            f"{int(_HEADLINE_SET_WIDTH_MAX / ratio)} characters, or "
                            "bring the hero size down."
                        ),
                    )
                )

    for role in _ROLES:
        leading = getattr(dtcg, role).leading.value
        if role in _PROSE_ROLES:
            if not _PROSE_LEADING_MIN <= leading <= _PROSE_LEADING_MAX:
                findings.append(
                    LintFinding(
                        rule="LINE_HEIGHT_OUT_OF_RANGE",
                        path=f"tokens.type.{role}.leading",
                        message=(
                            f"{leading} is outside {_PROSE_LEADING_MIN}-"
                            f"{_PROSE_LEADING_MAX} for text that wraps. Below the "
                            "floor the lines collide; above it the paragraph stops "
                            "cohering into one block."
                        ),
                    )
                )
        elif leading < _DISPLAY_LEADING_MIN:
            findings.append(
                LintFinding(
                    rule="LINE_HEIGHT_TOO_TIGHT",
                    path=f"tokens.type.{role}.leading",
                    message=(
                        f"{leading} is below {_DISPLAY_LEADING_MIN}. Display type can "
                        "run tight, but below this the ascenders of one line touch "
                        "the descenders of the one above."
                    ),
                )
            )
    return findings


def _check_rhythm(record: ArtDirectionRecord) -> list[LintFinding]:
    findings: list[LintFinding] = []
    rhythm = record.extensions.fluid.rhythm

    measure = rhythm.measure
    if measure.unit != "ch":
        findings.append(
            LintFinding(
                rule="MEASURE_NOT_IN_CHARACTERS",
                path="fluid.rhythm.measure",
                message=(
                    f"is in {measure.unit}. A measure is a count of characters — that "
                    "is what makes it hold across every type scale rather than being "
                    "re-derived per art direction."
                ),
            )
        )
    elif not _MEASURE_MIN_CH <= measure.value <= _MEASURE_MAX_CH:
        findings.append(
            LintFinding(
                rule="MEASURE_OUT_OF_RANGE",
                path="fluid.rhythm.measure",
                message=(
                    f"{measure.value}ch is outside {_MEASURE_MIN_CH:.0f}-"
                    f"{_MEASURE_MAX_CH:.0f}ch. Narrower and the eye returns too often; "
                    "wider and it loses the start of the next line."
                ),
            )
        )

    steps = [
        record.tokens.space.step1.value,
        record.tokens.space.step2.value,
        record.tokens.space.step3.value,
        record.tokens.space.step4.value,
        record.tokens.space.step5.value,
        record.tokens.space.step6.value,
        record.tokens.space.step7.value,
    ]
    for index, (lower, upper) in enumerate(pairwise(steps), start=1):
        if upper.value <= lower.value:
            findings.append(
                LintFinding(
                    rule="SPACING_NOT_INCREASING",
                    path=f"tokens.space.step{index + 1}",
                    message=(
                        f"{upper.value} is not larger than step{index}'s {lower.value}. "
                        "A spacing scale that does not increase gives two steps the "
                        "same meaning."
                    ),
                )
            )
            continue
        ratio = upper.value / lower.value
        if not _SPACE_RATIO_MIN <= ratio <= _SPACE_RATIO_MAX:
            findings.append(
                LintFinding(
                    rule="SPACING_RATIO_OUT_OF_RANGE",
                    path=f"tokens.space.step{index + 1}",
                    message=(
                        f"is {ratio:.2f}x step{index}, outside {_SPACE_RATIO_MIN}-"
                        f"{_SPACE_RATIO_MAX}. A step too close to its neighbour reads "
                        "as a mistake rather than a decision; one too far leaves a gap "
                        "with no value in it."
                    ),
                )
            )
    return findings


def _check_budgets(record: ArtDirectionRecord) -> list[LintFinding]:
    headline = record.extensions.budgets.headline
    if not _HEADLINE_BUDGET_MIN <= headline <= _HEADLINE_BUDGET_MAX:
        return [
            LintFinding(
                rule="HEADLINE_BUDGET_OUT_OF_RANGE",
                path="budgets.headline",
                message=(
                    f"{headline} characters is outside {_HEADLINE_BUDGET_MIN}-"
                    f"{_HEADLINE_BUDGET_MAX}. Below the floor no real headline fits "
                    "and the model is forced into fragments; above it the headline is "
                    "a paragraph set at display size."
                ),
            )
        ]
    return []


def _check_brand_mapping(record: ArtDirectionRecord) -> list[LintFinding]:
    """The one contradiction the two fields can express between them.

    `accent_role='bg'` says the brand becomes the ground and
    `allow_brand_background=False` says it may not, and a record holding both is
    not a design anybody chose — it is a `bg` typed into one field without the
    other. The types cannot rule it out, because each field is individually
    valid, so this is where it gets ruled out.

    Refused rather than resolved toward either half. Picking one would mean
    guessing whether a customer's colour is supposed to become their whole page,
    which is not a guess worth making silently.
    """
    mapping = record.extensions.brand_mapping
    if mapping.accent_role == "bg" and not mapping.allow_brand_background:
        return [
            LintFinding(
                rule="BRAND_BACKGROUND_NOT_ALLOWED",
                path="brandMapping.accentRole",
                message=(
                    "is 'bg', which puts the brand colour on the page ground, while "
                    "allowBrandBackground is false. One of the two is wrong and this "
                    "cannot tell which: set allowBrandBackground, or map the brand to "
                    "'accent' and leave the ground to the art direction."
                ),
            )
        ]
    return []


def _check_no_ramp_or_bloom(record: ArtDirectionRecord) -> list[LintFinding]:
    """Rules 18 and 19, asserted structurally rather than by inspection.

    **There is no token whose type could produce a gradient or a blur**, and
    that is the actual control — the schema has no ramp field, no shadow field
    and no blur field, so the artifact cannot contain one. This walks the
    serialized record for the words anyway, because the day someone adds a
    `filter` or a `boxShadow` token "just for one direction", this is what says
    no before the review does.
    """
    payload = record.model_dump(mode="json", by_alias=True)
    findings: list[LintFinding] = []
    for path, value in _all_strings(payload):
        lowered = value.lower()
        if "gradient" in lowered:
            findings.append(
                LintFinding(
                    rule="NO_RAMP",
                    path=path,
                    message=(
                        "names a gradient. Rule 18: colour transitions are carried by "
                        "texture — halftone, dither, weave — never by a ramp."
                    ),
                )
            )
        if "blur" in lowered or "shadow" in lowered:
            findings.append(
                LintFinding(
                    rule="NO_BLOOM",
                    path=path,
                    message=(
                        "names a blur or a shadow. Rule 19: a hard offset at zero blur "
                        "is a shape; a soft one is a bloom, and a bloom is the effect "
                        "rule 18 exists to prevent arriving by another route."
                    ),
                )
            )
    return findings


def _all_strings(node: object, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(node, str):
        return [(prefix or "(root)", node)]
    if isinstance(node, dict):
        found: list[tuple[str, str]] = []
        for key, child in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.append((path, str(key)))
            found.extend(_all_strings(child, path))
        return found
    if isinstance(node, list):
        found = []
        for index, child in enumerate(node):
            found.extend(_all_strings(child, f"{prefix}[{index}]"))
        return found
    return []
