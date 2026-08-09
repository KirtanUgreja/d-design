"""The two system art directions, in the v2 format.

Transcribed from `web/src/features/art-direction/cinematic-dark.ts` and
`editorial-light.ts`, which is the *only* time these numbers are typed twice.
There is no automated path from a TypeScript constant to a Python one, so the
transcription is checked rather than trusted: `api/tests/test_art_direction_seed.py`
pins this module to a JSON fixture, and `art-direction.test.ts` asserts that
`toCssVars(fromRecord(fixture))` is identical to `toCssVars` of the constant it
came from. **That equality is the migration's only real assertion** — a format
migration that changes a pixel has changed a design.

The design commentary that explains *why* each number is what it is stays in
the TypeScript files until they are deleted, and is not re-copied here. Two
copies of a paragraph is how a rationale becomes wrong in one place; the values
are what had to move.

Nothing here is improved on the way through. The v1 character caps become
`cinematic-dark`'s budgets exactly, as the phase asks, and `editorial-light`
gets the same ones — not because they are right for a smaller display face, but
because a migration that also changes behaviour is two changes wearing one
commit message. The field exists so `bold-brutalist` can disagree in phase 04,
and that is the first place a real divergence belongs.
"""

from pathlib import Path

from features.art_direction.dtcg import family, number, px, srgb, weight
from schema.art_direction import (
    ArtDirectionExtensions,
    ArtDirectionFluid,
    ArtDirectionRecord,
    BrandMapping,
    ClampTriple,
    ContentBudgets,
    DitherLayer,
    DtcgFonts,
    DtcgPalette,
    DtcgSpaceScale,
    DtcgTokens,
    DtcgTypeRole,
    DtcgTypeScale,
    DtcgVisual,
    FluidRhythm,
    FluidTypeRole,
    FluidTypeScale,
    GrainLayer,
    HalftoneLayer,
    ImageTreatment,
    Length,
    Ratio,
    SceneFit,
    SceneFitTable,
    WeaveLayer,
)

_FIXTURE_NAME = "art_directions.json"


# ---------------------------------------------------------------------------
# Length shorthands, mirroring `art-direction.ts`'s `rem()` / `px()` / `vw()`.
# The DTCG constructors of the same name build *tokens*; these build the fluid
# layer's plain lengths, and the two never meet — `dtcg.rem` is a `dimension`
# with a `$type`, `_rem` is a number and a unit inside `$extensions`.
# ---------------------------------------------------------------------------


def _rem(value: float) -> Length:
    return Length(value=value, unit="rem")


def _px(value: float) -> Length:
    return Length(value=value, unit="px")


def _vw(value: float) -> Length:
    return Length(value=value, unit="vw")


def _ch(value: float) -> Length:
    return Length(value=value, unit="ch")


def _svh(value: float) -> Length:
    return Length(value=value, unit="svh")


def _clamp(minimum: Length, preferred: Length, maximum: Length) -> ClampTriple:
    return ClampTriple(min=minimum, preferred=preferred, max=maximum)


def _fit(
    *,
    full_bleed: SceneFit,
    split_left: SceneFit,
    split_right: SceneFit,
    centered: SceneFit,
    stack: SceneFit,
    grid: SceneFit,
) -> SceneFitTable:
    """Keyword-only, by Python field name. `SceneFitTable`'s aliases are the
    layout's own spelling (`full-bleed`), which is not an identifier, and
    `**{"full-bleed": ...}` widens every value to `str` — losing exactly the
    check this table exists for."""
    return SceneFitTable(
        full_bleed=full_bleed,
        split_left=split_left,
        split_right=split_right,
        centered=centered,
        stack=stack,
        grid=grid,
    )


def _fixed(length: Length) -> ClampTriple:
    """One value three times. `to-css-vars.ts` emits `clamp()` unconditionally —
    one format, one parser, no branch for the case that happens to be fixed."""
    return _clamp(length, length, length)


# The v1 schema's character caps (`api/schema/scene.py`), which is where these
# lived before an art direction could hold them. `stat` is the *value's* cap
# rather than the label's: the value is the one set at display size, and it is
# the one that overflows.
_V1_BUDGETS = ContentBudgets(
    eyebrow=24,
    headline=60,
    body=240,
    quote=200,
    stat=12,
    list_item=80,
)


# ---------------------------------------------------------------------------
# cinematic-dark
# ---------------------------------------------------------------------------

_INK = "#f4f4f5"
_CINEMATIC_BG = "#08090b"
# Lightened from #f4b740 by phase 03's linter, which is the only reason it
# moved. The CTA sets `bg` on this fill — the most important text on the page —
# and at the old value that pair scored APCA Lc 70.6 against a required 75,
# while clearing WCAG 2.2 at 11.09:1. That gap is the whole argument for running
# both standards: the legal floor said it was fine and the perceptual gate said
# it was muddy, and on a near-black ground the perceptual gate is the one
# telling the truth. Same hue, ~2 points of headroom (Lc 79.5).
_CINEMATIC_ACCENT = "#fcca6d"

CINEMATIC_DARK = ArtDirectionRecord(
    id="cinematic-dark",
    version=1,
    name="Cinematic Dark",
    author="system",
    tokens=DtcgTokens(
        color=DtcgPalette(
            bg=srgb(_CINEMATIC_BG),
            bg_elevated=srgb("#101215"),
            ink=srgb(_INK),
            # 0.62 -> 0.85, also phase 03's linter. At 0.62 the muted body role
            # scored Lc 48 against a required 75 while clearing WCAG at 7.14:1.
            #
            # The finding underneath it is worth more than the number: **on a
            # near-black ground, opacity is not a viable hierarchy mechanism.**
            # The alpha range that clears Lc 75 against #08090b is 0.83-1.0, so
            # there is room for one step below full ink and not three. What
            # carries the rest of the hierarchy here is size, weight, case and
            # tracking — which the type scale was already doing.
            ink_muted=srgb(_INK, 0.85),
            # Unchanged, and no longer a text colour — see the eyebrow role
            # below. It stays in the palette as the faint ink a texture layer or
            # a hairline-adjacent surface can reference, where the text gates do
            # not apply.
            ink_faint=srgb(_INK, 0.5),
            accent=srgb(_CINEMATIC_ACCENT),
            accent_soft=srgb(_CINEMATIC_ACCENT, 0.12),
            veil=srgb(_CINEMATIC_BG, 0.72),
            hairline=srgb(_INK, 0.1),
        ),
        space=DtcgSpaceScale(
            step1=px(8),
            step2=px(16),
            step3=px(24),
            step4=px(40),
            step5=px(64),
            step6=px(96),
            step7=px(160),
        ),
        font=DtcgFonts(display=family("Fraunces"), text=family("Inter")),
        type=DtcgTypeScale(
            hero=DtcgTypeRole(
                leading=number(0.95), tracking=number(-0.03), weight=weight(500)
            ),
            section=DtcgTypeRole(
                leading=number(1.05), tracking=number(-0.02), weight=weight(500)
            ),
            lead=DtcgTypeRole(
                leading=number(1.5), tracking=number(-0.01), weight=weight(400)
            ),
            normal=DtcgTypeRole(
                leading=number(1.65), tracking=number(0), weight=weight(400)
            ),
            muted=DtcgTypeRole(
                leading=number(1.65), tracking=number(0), weight=weight(400)
            ),
            eyebrow=DtcgTypeRole(
                leading=number(1.2), tracking=number(0.14), weight=weight(500)
            ),
            stat=DtcgTypeRole(
                leading=number(1), tracking=number(-0.04), weight=weight(600)
            ),
        ),
        visual=DtcgVisual(strength=number(1)),
    ),
    extensions=ArtDirectionExtensions(
        budgets=_V1_BUDGETS,
        # Accents, and it stays dark. `allow_brand_background` is false because
        # a brand colour behind a full-bleed hero is not this direction — that
        # is what `bold-brutalist` is for, and the field exists so it can say so.
        brand_mapping=BrandMapping(
            accent_role="accent",
            allow_brand_background=False,
            logo_treatment="mono",
            contrast_strategy="auto",
        ),
        default_motion="cinematic-slow",
        fluid=ArtDirectionFluid(
            type=FluidTypeScale(
                hero=FluidTypeRole(
                    font="display", size=_clamp(_rem(3.5), _vw(8), _rem(8))
                ),
                section=FluidTypeRole(
                    font="display", size=_clamp(_rem(2), _vw(4.5), _rem(3.5))
                ),
                lead=FluidTypeRole(
                    font="text", size=_clamp(_rem(1.25), _vw(2), _rem(1.5))
                ),
                normal=FluidTypeRole(font="text", size=_fixed(_rem(1.0625))),
                muted=FluidTypeRole(
                    font="text", size=_fixed(_rem(1.0625)), color="inkMuted"
                ),
                eyebrow=FluidTypeRole(
                    font="text",
                    size=_fixed(_rem(0.8125)),
                    case="uppercase",
                    # `inkFaint` until phase 03. At 0.5 alpha it scored Lc 33.9
                    # against a required 75 — the worst failure in either art
                    # direction, and on the *smallest* text in the system, which
                    # is where APCA asks for the most rather than the least.
                    #
                    # Moved to `inkMuted` rather than raising `inkFaint`: at the
                    # alpha this role needs the two tokens would be 0.85 and
                    # 0.83, which is two names for one colour. The eyebrow keeps
                    # its quiet by being small, uppercase and tracked, which is
                    # what was doing the work anyway.
                    color="inkMuted",
                ),
                stat=FluidTypeRole(
                    font="display", size=_clamp(_rem(3), _vw(7), _rem(6))
                ),
            ),
            rhythm=FluidRhythm(
                scene_padding_y=_clamp(_rem(6), _vw(14), _rem(12)),
                scene_padding_x=_clamp(_rem(1.5), _vw(6), _rem(8)),
                measure=_ch(62),
                content_max=_px(1280),
                # Every layout owns the frame — deep space, one beat per screen.
                fit=_fit(
                    full_bleed="viewport",
                    split_left="viewport",
                    split_right="viewport",
                    centered="viewport",
                    stack="viewport",
                    grid="viewport",
                ),
                fit_min_block=_svh(100),
                fit_place="center",
                fit_scroll_margin=_rem(4),
            ),
            texture=[
                HalftoneLayer(
                    kind="halftone",
                    intensity=0.28,
                    color="accentSoft",
                    scale=_px(6),
                    offset=_px(0),
                    angle=15,
                    steps=3,
                ),
                DitherLayer(
                    kind="dither",
                    intensity=0.55,
                    color="bg",
                    scale=_px(3),
                    offset=_px(0),
                    steps=3,
                ),
                GrainLayer(
                    kind="grain",
                    intensity=0.05,
                    color="ink",
                    scale=_px(64),
                    offset=_px(0),
                    density=2,
                ),
            ],
            image=ImageTreatment(
                tone="duotone",
                overlay=GrainLayer(
                    kind="grain",
                    intensity=0.07,
                    color="ink",
                    scale=_px(64),
                    offset=_px(0),
                    density=2,
                ),
                frame="none",
                edge=_px(0),
                veil=0.45,
                ratios=[Ratio(w=21, h=9), Ratio(w=16, h=9)],
            ),
            visual_blend="screen",
        ),
    ),
)


# ---------------------------------------------------------------------------
# editorial-light
# ---------------------------------------------------------------------------

_EDITORIAL_BG = "#fbfcfd"
_EDITORIAL_INK = "#0f1115"
_EDITORIAL_ACCENT = "#9a2416"

EDITORIAL_LIGHT = ArtDirectionRecord(
    id="editorial-light",
    version=1,
    name="Editorial Light",
    author="system",
    tokens=DtcgTokens(
        color=DtcgPalette(
            bg=srgb(_EDITORIAL_BG),
            bg_elevated=srgb("#f1f3f6"),
            ink=srgb(_EDITORIAL_INK),
            ink_muted=srgb(_EDITORIAL_INK, 0.7),
            ink_faint=srgb(_EDITORIAL_INK, 0.55),
            accent=srgb(_EDITORIAL_ACCENT),
            accent_soft=srgb(_EDITORIAL_ACCENT, 0.1),
            veil=srgb(_EDITORIAL_BG, 0.82),
            hairline=srgb(_EDITORIAL_INK, 0.16),
        ),
        space=DtcgSpaceScale(
            step1=px(4),
            step2=px(8),
            step3=px(16),
            step4=px(24),
            step5=px(40),
            step6=px(64),
            step7=px(96),
        ),
        font=DtcgFonts(display=family("Newsreader"), text=family("Archivo")),
        type=DtcgTypeScale(
            hero=DtcgTypeRole(
                leading=number(1.05), tracking=number(-0.015), weight=weight(400)
            ),
            section=DtcgTypeRole(
                leading=number(1.15), tracking=number(-0.01), weight=weight(500)
            ),
            lead=DtcgTypeRole(
                leading=number(1.45), tracking=number(0), weight=weight(400)
            ),
            normal=DtcgTypeRole(
                leading=number(1.7), tracking=number(0.001), weight=weight(400)
            ),
            muted=DtcgTypeRole(
                leading=number(1.7), tracking=number(0.001), weight=weight(400)
            ),
            eyebrow=DtcgTypeRole(
                leading=number(1.2), tracking=number(0.1), weight=weight(600)
            ),
            stat=DtcgTypeRole(
                leading=number(1), tracking=number(-0.02), weight=weight(500)
            ),
        ),
        visual=DtcgVisual(strength=number(0.25)),
    ),
    extensions=ArtDirectionExtensions(
        budgets=_V1_BUDGETS,
        # The same four answers as `cinematic-dark`, written out rather than
        # defaulted since phase 04. Two art directions agreeing is not a default,
        # it is two art directions agreeing.
        brand_mapping=BrandMapping(
            accent_role="accent",
            allow_brand_background=False,
            logo_treatment="mono",
            contrast_strategy="auto",
        ),
        default_motion="editorial-restrained",
        fluid=ArtDirectionFluid(
            type=FluidTypeScale(
                hero=FluidTypeRole(
                    font="display", size=_clamp(_rem(2.5), _vw(5), _rem(4.5))
                ),
                section=FluidTypeRole(
                    font="display", size=_clamp(_rem(1.75), _vw(3), _rem(2.5))
                ),
                # The serif, not the sans — the clearest single place the two
                # typographic *systems* differ rather than their values.
                lead=FluidTypeRole(
                    font="display", size=_clamp(_rem(1.3125), _vw(1.8), _rem(1.5))
                ),
                normal=FluidTypeRole(font="text", size=_fixed(_rem(1))),
                muted=FluidTypeRole(
                    font="text", size=_fixed(_rem(1)), color="inkMuted"
                ),
                eyebrow=FluidTypeRole(
                    font="text",
                    size=_fixed(_rem(0.75)),
                    case="uppercase",
                    color="accent",
                ),
                stat=FluidTypeRole(
                    font="display", size=_clamp(_rem(2.5), _vw(4.5), _rem(4))
                ),
            ),
            rhythm=FluidRhythm(
                scene_padding_y=_clamp(_rem(3.5), _vw(7), _rem(6)),
                scene_padding_x=_clamp(_rem(1.25), _vw(4), _rem(4)),
                measure=_ch(68),
                content_max=_px(1080),
                # The table that makes the point: the frame-owning layouts own
                # the frame and the document-shaped ones do not.
                fit=_fit(
                    full_bleed="viewport",
                    split_left="viewport",
                    split_right="viewport",
                    centered="viewport",
                    stack="content",
                    grid="content",
                ),
                fit_min_block=_svh(100),
                fit_place="start",
                fit_scroll_margin=_rem(4),
            ),
            texture=[
                WeaveLayer(
                    kind="weave",
                    intensity=0.06,
                    color="ink",
                    scale=_px(7),
                    offset=_px(0),
                    density=2,
                )
            ],
            image=ImageTreatment(
                tone="as-shot",
                overlay=None,
                frame="hairline",
                edge=_px(0),
                veil=0.15,
                ratios=[Ratio(w=3, h=2), Ratio(w=4, h=5)],
            ),
            visual_blend="multiply",
        ),
    ),
)


# ---------------------------------------------------------------------------
# bold-brutalist — the one that breaks things
#
# The first art direction authored *into* this format rather than migrated into
# it, and the first judged by the linter while it was being written rather than
# after. Both of those change what it cost: nothing here was chosen and then
# checked, so the values below are already the ones that pass.
#
# **Its ground is a colour, not a neutral**, and that is the whole character.
# The other two answer "what surface is this page printed on" with black and
# with white; this one answers with ink. It is also what makes `accentRole:
# 'bg'` real — a brand kit does not tint this direction, it *replaces* the
# ground, and the page becomes the customer's colour at full strength.
#
# Process yellow rather than a violet or a magenta, and not only because
# principle 5 bans those: yellow is the one saturated hue with enough luminance
# to take near-black type at Lc 90+, which is what lets this direction be loud
# and legible at the same time. A saturated blue ground would have forced light
# ink and turned this into cinematic-dark with the contrast turned up.
# ---------------------------------------------------------------------------

_BRUTALIST_BG = "#f2e535"
_BRUTALIST_INK = "#0b0b0b"
# Authored at #b81400 and darkened by the linter before this file was ever
# committed — the third CTA-on-accent failure in three art directions, and by
# now a pattern rather than a coincidence. That pair is `bg`-coloured text on
# an `accent` fill, which is the one pair no type role describes and the only
# place in the system where the ground colour becomes the *text*. WCAG saw
# 5.11:1 and was content; APCA saw Lc 66.7 against 75.
#
# Deep oxide rather than a signal red, and that is what the measurement pushed
# it to: the yellow label needs the fill dark enough to sit on. It happens to be
# the right answer for the design too — yellow over deep red is a riso
# overprint, and a bright red would have been a second signal colour arguing
# with the ground.
_BRUTALIST_ACCENT = "#6e0a00"

BOLD_BRUTALIST = ArtDirectionRecord(
    id="bold-brutalist",
    version=1,
    name="Bold Brutalist",
    author="system",
    tokens=DtcgTokens(
        color=DtcgPalette(
            bg=srgb(_BRUTALIST_BG),
            # A hard white block, not a lifted surface. `bgElevated` means "the
            # other ground" rather than "the ground plus 6% white" — on a
            # coloured ground there is no elevation to express, and a yellow
            # nudged toward white is the muddy in-between this direction exists
            # to refuse.
            bg_elevated=srgb("#ffffff"),
            ink=srgb(_BRUTALIST_INK),
            # 0.88, and on a *light* ground the alpha actually works — which is
            # the other half of phase 03's finding rather than a contradiction
            # of it. The reason opacity failed as hierarchy on `cinematic-dark`
            # is that near-black leaves no room beneath full ink; a near-white
            # or a light-coloured ground leaves most of the range. Muted body
            # text here is Lc 90+, where cinematic-dark's was 48 at 0.62.
            ink_muted=srgb(_BRUTALIST_INK, 0.88),
            ink_faint=srgb(_BRUTALIST_INK, 0.62),
            accent=srgb(_BRUTALIST_ACCENT),
            accent_soft=srgb(_BRUTALIST_ACCENT, 0.15),
            veil=srgb(_BRUTALIST_BG, 0.82),
            # Full-strength ink, where the other two directions set 10% and 16%.
            # A rule in this direction is a black bar; its *weight* is the
            # `rule` texture layer's `thick`, not a washed-out colour. The role
            # is called `hairline` because that is what the other two use it
            # for, and a colour role named after one direction's use of it is
            # the naming mistake `DtcgSpaceScale` already refused to make.
            hairline=srgb(_BRUTALIST_INK),
        ),
        # Dense, and its own ratio rather than a halving of somebody else's:
        # roughly 1.65x per step where cinematic-dark runs 1.5-1.7 and
        # editorial-light runs 1.5-2.0. Tighter at the bottom, because
        # brutalist spacing is either nothing or a lot and the small steps are
        # the ones that have to disappear.
        space=DtcgSpaceScale(
            step1=px(6),
            step2=px(11),
            step3=px(20),
            step4=px(34),
            step5=px(56),
            step6=px(92),
            step7=px(150),
        ),
        font=DtcgFonts(display=family("Syne"), text=family("Space Grotesk")),
        type=DtcgTypeScale(
            # 0.86 leading against a floor of 0.85. Deliberately near the bound:
            # at 14rem the line gap *is* the composition, and a headline whose
            # second line does not lock into the first is not this direction.
            hero=DtcgTypeRole(
                leading=number(0.86), tracking=number(-0.05), weight=weight(800)
            ),
            section=DtcgTypeRole(
                leading=number(0.95), tracking=number(-0.04), weight=weight(800)
            ),
            lead=DtcgTypeRole(
                leading=number(1.4), tracking=number(-0.01), weight=weight(500)
            ),
            normal=DtcgTypeRole(
                leading=number(1.45), tracking=number(0), weight=weight(400)
            ),
            muted=DtcgTypeRole(
                leading=number(1.45), tracking=number(0), weight=weight(400)
            ),
            eyebrow=DtcgTypeRole(
                leading=number(1.2), tracking=number(0.08), weight=weight(700)
            ),
            stat=DtcgTypeRole(
                leading=number(0.9), tracking=number(-0.05), weight=weight(800)
            ),
        ),
        visual=DtcgVisual(strength=number(0.6)),
    ),
    extensions=ArtDirectionExtensions(
        budgets=ContentBudgets(
            eyebrow=20,
            # 34, and it is the number the type scale is *paid for* with. See
            # the two-tier scale-range rule in `lint.py`: this direction may run
            # hero at 13x body precisely because it also commits to a headline
            # that fits at that size. The budget is not a limitation here, it is
            # the consideration for the licence.
            headline=34,
            body=180,
            quote=140,
            stat=8,
            list_item=60,
        ),
        # The reason `allow_brand_background` is a field and not a constant.
        # `accent_role='bg'` moves the brand to the ground at full strength —
        # uncorrected, because a corrected brand ground is a brand colour this
        # direction decided it knew better than, which is the opposite of what
        # this direction offers.
        #
        # `contrast_strategy` stays `auto`: nothing here is corrected toward
        # anything, so there is no direction to declare. Phase 01 predicted this
        # would be the art direction that overrode it and it is not — see
        # docs/v2/plan/04-three-art-directions.md.
        brand_mapping=BrandMapping(
            accent_role="bg",
            allow_brand_background=True,
            logo_treatment="mono",
            contrast_strategy="auto",
        ),
        # ponytail: `mechanical-snap` is what this direction is actually for —
        # 220ms, hard cubic, no parallax (docs/v2/art-direction-system.md). It
        # is phase 11's build, and a seed naming a vocabulary that does not
        # exist is a broken foreign key wearing a design decision. Points at
        # `cinematic-slow` until then, which is wrong in character and correct
        # in referential integrity. Trigger: phase 11.
        default_motion="cinematic-slow",
        fluid=ArtDirectionFluid(
            type=FluidTypeScale(
                # The sketch says `clamp(4rem, 12vw, 14rem)` and this is
                # `10vw, 12rem`, which is a real deviation and worth its
                # reasoning: the sketch was written before this direction had a
                # typeface, and **Syne is a wide face.** At 12vw the word
                # "confidence" in the `full` fixture did not fit one line at
                # 1440px and broke mid-word, leaving a single orphaned "e" on
                # the line below. An aggressive break is a legitimate brutalist
                # device; a one-letter orphan reads as a bug, which is the
                # failure mode docs/v2/plan/04-three-art-directions.md names as
                # the one no automated check can catch.
                #
                # A token nobody has is what would have predicted it — the
                # linter measures size and budget and cannot know how wide a
                # glyph is. Recorded rather than tokenised: a per-face average
                # advance width is a real thing to add the day a fourth family
                # arrives, and inventing it for one data point would be fitting
                # a constant to a single observation.
                hero=FluidTypeRole(
                    font="display", size=_clamp(_rem(4), _vw(10), _rem(12))
                ),
                section=FluidTypeRole(
                    font="display", size=_clamp(_rem(2.5), _vw(5.5), _rem(4.5))
                ),
                lead=FluidTypeRole(
                    font="text", size=_clamp(_rem(1.375), _vw(2.2), _rem(1.75))
                ),
                normal=FluidTypeRole(font="text", size=_fixed(_rem(1.0625))),
                muted=FluidTypeRole(
                    font="text", size=_fixed(_rem(1.0625)), color="inkMuted"
                ),
                # `ink`, where editorial-light's eyebrow is `accent`. An eyebrow
                # in this direction is a black label, and its quiet comes from
                # being small, uppercase and tracked rather than from a colour.
                eyebrow=FluidTypeRole(
                    font="text",
                    size=_fixed(_rem(0.8125)),
                    case="uppercase",
                    color="ink",
                ),
                stat=FluidTypeRole(
                    font="display", size=_clamp(_rem(3.5), _vw(10), _rem(12))
                ),
            ),
            rhythm=FluidRhythm(
                # Half of cinematic-dark's, as the sketch asks. Density here is
                # not economy — the type is enormous, so the padding has to give
                # way or there is no room for a headline at all.
                scene_padding_y=_clamp(_rem(3), _vw(7), _rem(6)),
                scene_padding_x=_clamp(_rem(1), _vw(3), _rem(4)),
                measure=_ch(54),
                content_max=_px(1440),
                # Every layout owns the frame, like cinematic-dark — but placed
                # at `end` rather than `center`. Type jammed to the baseline
                # with the empty room above it is most of what this direction
                # is, and it is the first use of a token authored in phase 13
                # for exactly this direction.
                fit=_fit(
                    full_bleed="viewport",
                    split_left="viewport",
                    split_right="viewport",
                    centered="viewport",
                    stack="viewport",
                    grid="viewport",
                ),
                fit_min_block=_svh(100),
                fit_place="end",
                fit_scroll_margin=_rem(4),
            ),
            # Riso misregistration: the same halftone twice, in two token
            # colours, one nudged 3px. This is the arrangement the texture list
            # was made indexed rather than keyed-by-kind to allow, and this is
            # the first art direction that actually uses it.
            #
            # "Halftone at full strength" in the sketch is read as `steps=2` —
            # the hardest banding the vocabulary offers — and not as
            # `intensity=1`. A 100%-opacity dot screen behind body copy is not a
            # strong art direction, it is unreadable text, and the linter cannot
            # see it because the linter measures flat colours.
            texture=[
                HalftoneLayer(
                    kind="halftone",
                    intensity=0.3,
                    color="accent",
                    scale=_px(10),
                    offset=_px(0),
                    angle=45,
                    steps=2,
                ),
                HalftoneLayer(
                    kind="halftone",
                    intensity=0.26,
                    color="ink",
                    scale=_px(10),
                    offset=_px(3),
                    angle=45,
                    steps=2,
                ),
                # A third layer — `rule`, block axis, thick, full-strength ink —
                # was authored here and removed after looking at it, which is
                # the same conclusion `editorial-light` reached in v1 and the
                # same one recorded in docs/v2/art-direction-system.md: a rule
                # repeated across a whole scene is ruled paper, not structure.
                # At full ink under a black headline it was worse than that, the
                # bars and the letterforms merging into one shape.
                #
                # **A visible rule is furniture, not ground.** It belongs to
                # phase 17's `Furniture` group, where it can be placed once
                # rather than tiled. That this art direction rediscovered a
                # finding the docs already held is the argument for `rule`
                # leaving the texture union altogether — noted there rather than
                # acted on here, because removing a kind is a renderer change.
            ],
            image=ImageTreatment(
                tone="posterize",
                overlay=HalftoneLayer(
                    kind="halftone",
                    intensity=0.35,
                    color="ink",
                    scale=_px(8),
                    offset=_px(0),
                    angle=45,
                    steps=2,
                ),
                frame="block",
                edge=_px(0),
                veil=0.2,
                ratios=[Ratio(w=1, h=1), Ratio(w=4, h=3)],
            ),
            visual_blend="multiply",
        ),
    ),
)


# Keyed by `(id, version)`, which is the primary key in migration 0008 and
# therefore the only identity these have. The migration iterates this; nothing
# else decides which system art directions exist.
SYSTEM_ART_DIRECTIONS: tuple[ArtDirectionRecord, ...] = (
    CINEMATIC_DARK,
    EDITORIAL_LIGHT,
    BOLD_BRUTALIST,
)


# The wire form of the two, and where it is checked in.
#
# Both live here rather than in `scripts/export_art_directions.py` because the
# script is a CLI wrapper and this is the fact: these records have one wire
# shape, and one file that both languages read it from. `scripts/` is not a
# package, so a test importing from it is also a module-resolution problem
# nobody should have to think about.
FIXTURE = Path(__file__).resolve().parents[2] / "schema" / "fixtures" / _FIXTURE_NAME


def wire_payload() -> list[dict[str, object]]:
    """camelCase aliases, `$type`/`$value` as the DTCG spec spells them — what
    the API serves and therefore what `web` parses, rather than Python's own
    field names."""
    return [
        record.model_dump(mode="json", by_alias=True, exclude_none=True)
        for record in SYSTEM_ART_DIRECTIONS
    ]
