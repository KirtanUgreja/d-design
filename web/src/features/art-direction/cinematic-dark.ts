// Art direction #1. Deep space, large light type, slow confident motion —
// docs/v1/art-direction.md, and the hand-designed comps in docs/v1/comps/ are
// what these numbers were measured against.
//
// Chosen for v1 because it is forgiving of sparse content: negative space
// reads as intentional rather than unfinished. `editorial-light` is the
// opposite bet and is deliberately the harder one.
//
// Values only. The types moved to `art-direction.ts` when there were two of
// these.

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

const BG = hex('#08090b');
const INK = hex('#f4f4f5');
// Corrected from phase 02's draft 0.38 -> 0.50: measured 3.28:1 against --bg,
// which fails 4.5:1 for the 13px eyebrow text it colors (small text, not
// large text, under WCAG). See docs/v1/comps/tokens.css for the numbers.
const INK_FAINT_ALPHA = 0.5;
const ACCENT = hex('#f4b740'); // verified 11.09:1 against --bg in phase 02

export const CINEMATIC_PALETTE: Palette = {
  bg: BG,
  bgElevated: hex('#101215'),
  ink: INK,
  inkMuted: withAlpha(INK, 0.62),
  inkFaint: withAlpha(INK, INK_FAINT_ALPHA),
  accent: ACCENT,
  accentSoft: withAlpha(ACCENT, 0.12),
  veil: withAlpha(BG, 0.72),
  hairline: withAlpha(INK, 0.1),
};

export const TYPE_SCALE: Record<TypeRoleKey, TypeRole> = {
  hero: {
    font: 'display',
    size: { min: rem(3.5), preferred: vw(8), max: rem(8) },
    leading: 0.95,
    tracking: -0.03,
    weight: 500,
  },
  section: {
    font: 'display',
    size: { min: rem(2), preferred: vw(4.5), max: rem(3.5) },
    leading: 1.05,
    tracking: -0.02,
    weight: 500,
  },
  lead: {
    font: 'text',
    size: { min: rem(1.25), preferred: vw(2), max: rem(1.5) },
    leading: 1.5,
    tracking: -0.01,
    weight: 400,
  },
  normal: {
    font: 'text',
    size: fixed(rem(1.0625)),
    leading: 1.65,
    tracking: 0,
    weight: 400,
  },
  muted: {
    font: 'text',
    size: fixed(rem(1.0625)),
    leading: 1.65,
    tracking: 0,
    weight: 400,
    color: 'inkMuted',
  },
  eyebrow: {
    font: 'text',
    size: fixed(rem(0.8125)),
    leading: 1.2,
    tracking: 0.14,
    weight: 500,
    case: 'uppercase',
    color: 'inkFaint',
  },
  stat: {
    font: 'display',
    size: { min: rem(3), preferred: vw(7), max: rem(6) },
    leading: 1,
    tracking: -0.04,
    weight: 600,
  },
};

export const CINEMATIC_RHYTHM: Rhythm = {
  space: [px(8), px(16), px(24), px(40), px(64), px(96), px(160)],
  scenePaddingY: { min: rem(6), preferred: vw(14), max: rem(12) },
  scenePaddingX: { min: rem(1.5), preferred: vw(6), max: rem(8) },
  measure: ch(62),
  contentMax: px(1280),
  // Every layout owns the frame. This is the direction the spec calls forgiving
  // of sparse content, and the reason it is forgiving is that four words on a
  // full black screen is the effect — the same four words at content height are
  // a caption floating above the next scene's headline.
  fit: {
    'full-bleed': 'viewport',
    'split-left': 'viewport',
    'split-right': 'viewport',
    centered: 'viewport',
    stack: 'viewport',
    grid: 'viewport',
  },
  fitMinBlock: svh(100),
  fitPlace: 'center',
  fitScrollMargin: rem(4),
};

/** Re-authored, not stripped. The v1 version was `grain + glow + vignette`,
 * and two of those three were radial gradients — the glow a coloured bloom
 * behind every hero, which is the single most on-the-nose violation of
 * principle 5 the artifact contained.
 *
 * The bloom becomes a **three-step dot field**: dense dots at the light
 * source, a middle band, a sparse band, hard boundaries between them. On a
 * black stage that reads as light with a printed grain, and it is
 * unmistakably not a mesh. The vignette becomes a **dithered edge** — a Bayer
 * dissolve inward from the frame in three bands, which is the classic
 * non-gradient vignette and looks like a choice, which the radial one never
 * did. Grain survives in character and is a mask now, so it takes its colour
 * from a token like everything else. */
export const CINEMATIC_TEXTURE: Texture = [
  {
    kind: 'halftone',
    intensity: 0.28,
    color: 'accentSoft',
    scale: px(6),
    offset: px(0),
    // Off-orthogonal on purpose. A dot lattice at 0 or 45 degrees reads as a
    // grid or a check; the classic print screen angles avoid both.
    angle: 15,
    steps: 3,
  },
  { kind: 'dither', intensity: 0.55, color: 'bg', scale: px(3), offset: px(0), steps: 3 },
  {
    kind: 'grain',
    intensity: 0.05,
    color: 'ink',
    scale: px(64),
    offset: px(0),
    density: 2,
  },
];

/** Ink to accent, grain over the top, no frame, wide crops. A photograph on
 * this stage should read as lit by the same source as everything else — the
 * duotone is what does that, and it is two flat token colours through two
 * blend modes rather than a filter or a ramp. */
export const CINEMATIC_IMAGE: ImageTreatment = {
  tone: 'duotone',
  // The same grain the ground carries, so the photograph shares its surface.
  overlay: {
    kind: 'grain',
    intensity: 0.07,
    color: 'ink',
    scale: px(64),
    offset: px(0),
    density: 2,
  },
  frame: 'none',
  edge: px(0),
  // Enough to hold a hero headline over a bright photograph. Flat, not a
  // bottom-up scrim, which would be a gradient.
  veil: 0.45,
  // Cinema, and the letterbox is the point.
  ratios: [
    { w: 21, h: 9 },
    { w: 16, h: 9 },
  ],
};

export const CINEMATIC_DARK: ArtDirection = {
  id: 'cinematic-dark',
  color: CINEMATIC_PALETTE,
  fonts: { display: 'fraunces', text: 'inter' },
  type: TYPE_SCALE,
  rhythm: CINEMATIC_RHYTHM,
  texture: CINEMATIC_TEXTURE,
  image: CINEMATIC_IMAGE,
  visualBlend: 'screen',
  // The scale the generators were authored and reviewed against, over a real
  // photograph, in phase 11. This direction is the reference; the token exists
  // so another one need not be.
  visualStrength: 1,
};
