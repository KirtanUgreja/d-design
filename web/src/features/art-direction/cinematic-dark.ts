// The four token groups that live together as one `ArtDirection` object —
// Color, Type, Rhythm, Texture. Motion is the fifth group in art-direction.md
// but ships separately, in motion-vocabulary.ts: the renderer core takes
// `motion` as its own parameter so the reduced-motion swap can happen without
// touching anything else (docs/coderules/patterns.md rule 2).
//
// "A token whose type is 'any string' is a token that will have to be
// redesigned" (docs/v1/art-direction.md). Every group below is typed to that
// standard: color is channels, never a hex string; sizes are clamp triples of
// `Length`, never a CSS string; fonts are registry ids, never family strings.

import type { Block } from '@/schema';

import { type Color, parseHex, withAlpha } from './color';

// ---------------------------------------------------------------------------
// Type keys, derived from the schema rather than re-typed. `Block` is the
// public surface's export; `HeadlineProps`/`BodyProps` are not, so the
// emphasis unions are projected out of the union member by discriminant
// rather than widening the schema index for two internal shapes. If a role
// is added to `emphasis` on either block, `TypeRoleKey` picks it up
// automatically and `TYPE_SCALE` below fails to compile until the token is
// added — that is the whole point (phase 03's Verify: "add a role without
// adding a token and it is a type error").
// ---------------------------------------------------------------------------

type PropsOf<T extends Block['props']['type']> = Extract<Block['props'], { type: T }>;
type HeadlineEmphasis = NonNullable<PropsOf<'headline'>['emphasis']>; // 'hero' | 'section'
type BodyEmphasis = NonNullable<PropsOf<'body'>['emphasis']>; // 'lead' | 'normal' | 'muted'
export type TypeRoleKey = HeadlineEmphasis | BodyEmphasis | 'eyebrow' | 'stat';

// ---------------------------------------------------------------------------
// Length / clamp — a `clamp(min, preferred, max)` triple where each part can
// carry its own unit, because that is how the real values are written
// (`clamp(3.5rem, 8vw, 8rem)` mixes rem and vw). A plain `Length` is a
// one-part value with no clamping.
// ---------------------------------------------------------------------------

export type Unit = 'px' | 'rem' | 'ch' | 'vw' | 'vh' | '%';

export interface Length {
  value: number;
  unit: Unit;
}

export interface ClampTriple {
  min: Length;
  preferred: Length;
  max: Length;
}

const rem = (value: number): Length => ({ value, unit: 'rem' });
const px = (value: number): Length => ({ value, unit: 'px' });
const vw = (value: number): Length => ({ value, unit: 'vw' });
const ch = (value: number): Length => ({ value, unit: 'ch' });

const fixed = (l: Length): ClampTriple => ({ min: l, preferred: l, max: l });

// ---------------------------------------------------------------------------
// Color
// ---------------------------------------------------------------------------

export interface Palette {
  bg: Color;
  bgElevated: Color;
  ink: Color;
  inkMuted: Color;
  inkFaint: Color;
  accent: Color;
  accentSoft: Color;
  veil: Color;
  hairline: Color;
}

// Parsed once, here, at the point a literal enters the typed system — never
// held as a string past this line. `parseHex` returning a Result is the
// right shape for user input; a hand-written constant that fails to parse is
// a bug in this file, so it throws rather than threading a Result through a
// module-level initializer nothing can react to.
function hex(value: string): Color {
  const result = parseHex(value);
  if (!result.ok) throw new Error(`cinematic-dark.ts: ${result.error.message}`);
  return result.value;
}

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

// ---------------------------------------------------------------------------
// Type
// ---------------------------------------------------------------------------

/** The font registry: id -> a vetted family and its Fontsource weights. Four
 * lines, and the thing that stops the most natural-looking free-text token
 * in the whole system — a font-family string — from ever existing. */
export const FONT_REGISTRY = {
  display: { family: 'Fraunces', weights: [400, 500, 600] as const },
  text: { family: 'Inter', weights: [400, 500, 600] as const },
} as const;

export type FontRegistryId = keyof typeof FONT_REGISTRY;

export interface TypeRole {
  font: FontRegistryId;
  size: ClampTriple;
  leading: number; // unitless line-height
  tracking: number; // em
  weight: (typeof FONT_REGISTRY)[FontRegistryId]['weights'][number];
  case?: 'uppercase';
  color?: keyof Palette;
}

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

// ---------------------------------------------------------------------------
// Rhythm — logical, not physical. Consumers apply every one of these through
// -inline/-block properties; the token itself is direction-agnostic.
// ---------------------------------------------------------------------------

export interface Rhythm {
  space: readonly [Length, Length, Length, Length, Length, Length, Length];
  scenePaddingY: ClampTriple;
  scenePaddingX: ClampTriple;
  measure: Length;
  contentMax: Length;
}

export const CINEMATIC_RHYTHM: Rhythm = {
  space: [px(8), px(16), px(24), px(40), px(64), px(96), px(160)],
  scenePaddingY: { min: rem(6), preferred: vw(14), max: rem(12) },
  scenePaddingX: { min: rem(1.5), preferred: vw(6), max: rem(8) },
  measure: ch(62),
  contentMax: px(1280),
};

// ---------------------------------------------------------------------------
// Texture — an ordered list of layers, never a bare string. `none` is the
// empty array; there is no separate "off" variant to keep in sync.
// ---------------------------------------------------------------------------

export interface TextureLayer {
  kind: 'grain' | 'glow' | 'vignette';
  intensity: number; // 0-1
}

export type Texture = readonly TextureLayer[];

export const CINEMATIC_TEXTURE: Texture = [
  { kind: 'grain', intensity: 0.04 },
  { kind: 'glow', intensity: 1 },
  { kind: 'vignette', intensity: 1 },
];

// ---------------------------------------------------------------------------
// The art direction
// ---------------------------------------------------------------------------

export interface ArtDirection {
  id: 'cinematic-dark';
  color: Palette;
  type: Record<TypeRoleKey, TypeRole>;
  rhythm: Rhythm;
  texture: Texture;
}

export const CINEMATIC_DARK: ArtDirection = {
  id: 'cinematic-dark',
  color: CINEMATIC_PALETTE,
  type: TYPE_SCALE,
  rhythm: CINEMATIC_RHYTHM,
  texture: CINEMATIC_TEXTURE,
};
