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
  Palette,
  Rhythm,
  Texture,
  TypeRole,
  TypeRoleKey,
} from './art-direction';
import { ch, fixed, hex, px, rem, vw } from './art-direction';
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
};

/** Empty, and that is a real answer rather than a gap left unfilled. The
 * texture vocabulary is grain/glow/vignette — three effects that all assume a
 * dark ground and a light source. On white, every one of them is dirt.
 *
 * What this direction wants instead is hairline rules, and it gets them from
 * `--hairline` where the renderer already draws borders. A fourth texture kind
 * would be a renderer change, which is exactly the cost this exercise is
 * measuring, so it was not taken. Noted in `art-direction.ts`. */
export const EDITORIAL_TEXTURE: Texture = [];

export const EDITORIAL_LIGHT: ArtDirection = {
  id: 'editorial-light',
  color: EDITORIAL_PALETTE,
  fonts: { display: 'newsreader', text: 'archivo' },
  type: EDITORIAL_TYPE_SCALE,
  rhythm: EDITORIAL_RHYTHM,
  texture: EDITORIAL_TEXTURE,
  // Ink, not light. See `VisualBlend` — this one token is what keeps the
  // AbstractVisual generators meaningful on paper.
  visualBlend: 'multiply',
  // A quarter. Ink on paper is read at a glance where light on black is read as
  // depth, so the same opacity that is atmosphere on #08090b is a stain on
  // #fbfcfd — measured by looking at it, which is the only way this number was
  // ever going to be found.
  visualStrength: 0.25,
};
