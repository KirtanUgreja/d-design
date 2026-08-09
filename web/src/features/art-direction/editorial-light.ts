// Art direction #2 — the falsification test.
//
// docs/v1/spec.md, Risk 4: "the art-direction layer is unproven until there
// are two. v1 ships one, so the central claim — that variety is cheap — is
// asserted, not demonstrated. First priority after v1 is art direction #2,
// and if it requires renderer changes, the abstraction is wrong."
//
// **Bright printed page, small confident type, motion that arrives rather than
// drifts.** Deliberately the hard case, and deliberately not "cinematic-dark
// with the colours flipped":
//
// | | cinematic-dark | editorial-light |
// |---|---|---|
// | ground | near-black, glow, vignette, grain | bright cool white, no texture at all |
// | hero | `clamp(3.5rem, 8vw, 8rem)`, tracking -0.03 | `clamp(2.5rem, 5vw, 4.5rem)`, tracking -0.015 |
// | measure | 62ch on a 1280px canvas | 68ch on a 1080px canvas — a column, not a stage |
// | scene padding | up to 12rem block | up to 6rem block, and half the inline |
// | accent | warm amber, used as light | oxide red, used as ink |
// | motion | 900ms expo drift, 120ms stagger | 320ms, 40ms stagger, no parallax travel |
//
// The two are not the same design at different brightnesses: one is a stage
// with a spotlight, the other is a printed spread. That is the claim.
//
// **Three constraints from docs/design/brand.md, which are not this file's to
// relitigate.** Our own chrome is a light warm-neutral editorial wall, and if
// the two converge, "this product makes exactly one thing" comes back as "this
// product has a house style". So: a different display face (ours is a licensed
// editorial face; this is Newsreader), a different ground (ours is warm paper;
// this is cool white), and a much louder accent (ours appears twice on a
// screen; this one carries the eyebrows, the rules and the CTA).
//
// **Density is a token decision, and this is the direction that proves it.**
// The v1 acceptance run recorded that "a scene is not a screen" — scenes came
// out 800/779/628/505/1227 tall in an 800px window under cinematic-dark. There
// is no `min-height` anywhere in the renderer; that height was `scenePaddingY`
// plus content, i.e. entirely this layer's doing. editorial-light halves the
// block padding on purpose, because a printed spread is *meant* to run
// continuously rather than break at the fold.

import type {
  ArtDirection,
  ImageTreatment,
  Palette,
  Rhythm,
  Texture,
  TypeRole,
  TypeRoleKey,
} from './art-direction';
import { ch, fixed, hex, px, rem, svh, vw } from './art-direction';
import { withAlpha } from './color';

// Cool white, not #fff: paper that is very slightly blue reads as bright,
// where pure white reads as an unpainted div. The inverse of cinematic-dark's
// reason for avoiding #000.
const BG = hex('#fbfcfd');
// Near-black with a trace of blue, never #000 — same reason.
const INK = hex('#0f1115');
// Oxide red. Loud enough to carry rules and eyebrows, and it is the one hue
// that cannot be mistaken for cinematic-dark's amber when the two are two
// inches apart in the editor. Measured 6.48:1 against --bg, which clears
// 4.5:1 for the smallest text it colours (the 12px eyebrow).
const ACCENT = hex('#9a2416');

export const EDITORIAL_PALETTE: Palette = {
  bg: BG,
  // *Darker* than bg, not lighter. On a light ground "elevated" cannot mean
  // "closer to white" — there is nowhere to go — so a framed surface recedes
  // instead. Nothing in the renderer assumes a direction; it reads a token.
  bgElevated: hex('#f1f3f6'),
  ink: INK,
  inkMuted: withAlpha(INK, 0.7),
  // 0.7/0.55 rather than cinematic-dark's 0.62/0.5: dark ink on a light ground
  // loses contrast faster per step of alpha than light ink on a dark one, so
  // the same-looking hierarchy needs different numbers. Measured, not copied.
  inkFaint: withAlpha(INK, 0.55),
  accent: ACCENT,
  // 0.1 rather than 0.12, and it means something different here — on white it
  // is a wash behind a pull quote, not a glow.
  accentSoft: withAlpha(ACCENT, 0.1),
  veil: withAlpha(BG, 0.82),
  // Hairlines do the work texture does in cinematic-dark, so they are darker
  // relative to the ground than that direction's are: 0.16 of near-black.
  hairline: withAlpha(INK, 0.16),
};

export const EDITORIAL_TYPE_SCALE: Record<TypeRoleKey, TypeRole> = {
  // Half the size of cinematic-dark's hero, and that is the point. A printed
  // page earns attention with position and white space; a stage earns it with
  // scale. Tracking is much closer to neutral because Newsreader at 4rem does
  // not need help tightening the way Fraunces at 8rem does.
  hero: {
    font: 'display',
    size: { min: rem(2.5), preferred: vw(5), max: rem(4.5) },
    leading: 1.05,
    tracking: -0.015,
    weight: 400,
  },
  section: {
    font: 'display',
    size: { min: rem(1.75), preferred: vw(3), max: rem(2.5) },
    leading: 1.15,
    tracking: -0.01,
    weight: 500,
  },
  // The lede of an article: the serif, not the sans, and set larger than the
  // body it introduces. cinematic-dark's `lead` is the text face; this is the
  // clearest single place the two typographic *systems* differ rather than
  // their values.
  lead: {
    font: 'display',
    size: { min: rem(1.3125), preferred: vw(1.8), max: rem(1.5) },
    leading: 1.45,
    tracking: 0,
    weight: 400,
  },
  normal: {
    font: 'text',
    size: fixed(rem(1)),
    leading: 1.7,
    tracking: 0.001,
    weight: 400,
  },
  muted: {
    font: 'text',
    size: fixed(rem(1)),
    leading: 1.7,
    tracking: 0.001,
    weight: 400,
    color: 'inkMuted',
  },
  // The accent's smallest use, and therefore the one that decides whether the
  // accent passes at all. Coloured rather than faint — on a light ground a
  // faint eyebrow is a smudge, where on a dark one it is a whisper.
  eyebrow: {
    font: 'text',
    size: fixed(rem(0.75)),
    leading: 1.2,
    tracking: 0.1,
    weight: 600,
    case: 'uppercase',
    color: 'accent',
  },
  // A newspaper's big number: display face, roman rather than heavy, and much
  // smaller than cinematic-dark's — it sits in a column, not across a stage.
  stat: {
    font: 'display',
    size: { min: rem(2.5), preferred: vw(4.5), max: rem(4) },
    leading: 1,
    tracking: -0.02,
    weight: 500,
  },
};

export const EDITORIAL_RHYTHM: Rhythm = {
  // A tighter scale than cinematic-dark's, and it is not the same numbers
  // scaled: the small end is finer (4px exists, for hairline-adjacent gaps)
  // and the top is much lower, because nothing on a printed page is 160px
  // from anything else.
  space: [px(4), px(8), px(16), px(24), px(40), px(64), px(96)],
  scenePaddingY: { min: rem(3.5), preferred: vw(7), max: rem(6) },
  scenePaddingX: { min: rem(1.25), preferred: vw(4), max: rem(4) },
  // Wider measure, narrower canvas: a column of text you read, rather than a
  // stage you look at.
  measure: ch(68),
  contentMax: px(1080),
  // The table that makes the point. A printed spread pads a *plate* to the full
  // page and lets a spec table end where the data ends — padding a six-row
  // table to full height does not read as generous, it reads as a bug. So the
  // frame-owning layouts own the frame and the document-shaped ones do not.
  //
  // Splits are `viewport` deliberately: a split is a plate and a column, and a
  // half-height split is neither. That is a judgement, and the point of it
  // being in this table is that changing it is a token edit.
  fit: {
    'full-bleed': 'viewport',
    'split-left': 'viewport',
    'split-right': 'viewport',
    centered: 'viewport',
    stack: 'content',
    grid: 'content',
  },
  fitMinBlock: svh(100),
  // Paper sets type from the top of the text block, not the optical middle of
  // the page. The one place this direction disagrees with cinematic-dark about
  // placement, and it is why the token exists.
  fitPlace: 'start',
  fitScrollMargin: rem(4),
};

/** This was `[]` in v1, with a comment saying the empty array was a real
 * answer because grain/glow/vignette all assume a dark ground and a light
 * source, and on white every one of them is dirt. That was true, and it also
 * recorded the gap: *"what this direction wants instead is hairline rules"*,
 * declined because a fourth kind was a renderer change.
 *
 * Phase 14 paid that cost, so the gap gets filled with what the note asked
 * for. Weave is the tooth of uncoated stock and is the quietest kind in the
 * vocabulary; the rules are the baseline grid showing through. Neither one
 * assumes a light source, which is the property the v1 three all lacked. */
export const EDITORIAL_TEXTURE: Texture = [
  {
    kind: 'weave',
    intensity: 0.06,
    color: 'ink',
    scale: px(7),
    offset: px(0),
    density: 2,
  },
];

/* Weave only — and the `rule` layer that was here got deleted after looking at
 * it, which is the review this phase says is the one most likely to be skipped.
 *
 * A hairline `rule` every 32px across the whole scene does not read as a
 * printed spread. It reads as **ruled notebook paper**, and it was worse than
 * the empty array v1 shipped. The mistake was a category error rather than a
 * value: in print a baseline grid is *invisible*, and a rule you can see is
 * structural — under a running head, between columns, closing a section.
 *
 * So the kind stays in the vocabulary (`bold-brutalist` will want inline rules,
 * and they had to exist before an art direction could ask for them), but the
 * thing v1's note actually wanted is furniture, not ground. That is
 * `Furniture { rule, ruleWeight }` in phase 17, which already has the fields
 * for it — the gap was real and this was the wrong place to close it. */

/** A printed photograph: shown close to as-shot, ruled rather than bled, in
 * the crops a magazine actually uses. The deliberate opposite of
 * cinematic-dark's answer at every field, from the same type — which is the
 * whole test. */
export const EDITORIAL_IMAGE: ImageTreatment = {
  // Paper reproduces a photograph; a stage relights it.
  tone: 'as-shot',
  overlay: null,
  // The hairline this direction uses everywhere else, around the plate.
  frame: 'hairline',
  edge: px(0),
  // Much lower. Text sits *beside* images here rather than on them.
  veil: 0.15,
  ratios: [
    { w: 3, h: 2 },
    { w: 4, h: 5 },
  ],
};

export const EDITORIAL_LIGHT: ArtDirection = {
  id: 'editorial-light',
  color: EDITORIAL_PALETTE,
  fonts: { display: 'newsreader', text: 'archivo' },
  type: EDITORIAL_TYPE_SCALE,
  rhythm: EDITORIAL_RHYTHM,
  texture: EDITORIAL_TEXTURE,
  image: EDITORIAL_IMAGE,
  // Ink, not light. See `VisualBlend` — this one token is what keeps the
  // AbstractVisual generators meaningful on paper.
  visualBlend: 'multiply',
  // A quarter. Ink on paper is read at a glance where light on black is read as
  // depth, so the same opacity that is atmosphere on #08090b is a stain on
  // #fbfcfd — measured by looking at it, which is the only way this number was
  // ever going to be found.
  visualStrength: 0.25,
};
