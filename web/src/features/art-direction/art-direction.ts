// What an art direction *is* — the four token groups as types, and nothing
// that is one particular art direction.
//
// This file did not exist until there were two. Every type in it lived in
// `cinematic-dark.ts` alongside the values, which is the shape a system takes
// when it has one instance and has never been asked to have another: the
// instance and the interface are the same file, and nothing forces you to
// notice. Splitting them was the first thing `editorial-light` cost, and it
// cost nothing else structural — docs/v1/art-direction.md's test is "if it
// requires *any* renderer change, the abstraction is wrong", and this is not
// the renderer.
//
// "A token whose type is 'any string' is a token that will have to be
// redesigned" (docs/v1/art-direction.md). Every group below is typed to that
// standard: color is channels, never a hex string; sizes are clamp triples of
// `Length`, never a CSS string; fonts are registry ids, never family strings.

import type { Block } from '@/schema';

import { type Color, parseHex } from './color';

// ---------------------------------------------------------------------------
// Type keys, derived from the schema rather than re-typed. `Block` is the
// public surface's export; `HeadlineProps`/`BodyProps` are not, so the
// emphasis unions are projected out of the union member by discriminant
// rather than widening the schema index for two internal shapes. If a role
// is added to `emphasis` on either block, `TypeRoleKey` picks it up
// automatically and every art direction's scale fails to compile until the
// token is added — that is the whole point (phase 03's Verify: "add a role
// without adding a token and it is a type error").
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

export const rem = (value: number): Length => ({ value, unit: 'rem' });
export const px = (value: number): Length => ({ value, unit: 'px' });
export const vw = (value: number): Length => ({ value, unit: 'vw' });
export const ch = (value: number): Length => ({ value, unit: 'ch' });

export const fixed = (l: Length): ClampTriple => ({ min: l, preferred: l, max: l });

/** Parsed once, at the point a literal enters the typed system — never held as
 * a string past this line. `parseHex` returning a Result is the right shape
 * for user input; a hand-written constant that fails to parse is a bug in the
 * file that wrote it, so this throws rather than threading a Result through a
 * module-level initializer nothing can react to. */
export function hex(value: string): Color {
  const result = parseHex(value);
  if (!result.ok) throw new Error(`art direction: ${result.error.message}`);
  return result.value;
}

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

// ---------------------------------------------------------------------------
// Type
// ---------------------------------------------------------------------------

/** The font registry: id -> a vetted family and its Fontsource weights. The
 * thing that stops the most natural-looking free-text token in the whole
 * system — a font-family string — from ever existing.
 *
 * Keyed by **family**, not by role. It was keyed by role (`display`, `text`)
 * while there was one art direction, which made the two families global: a
 * second art direction could pick different sizes and colours but was stuck
 * with Fraunces and Inter. That is the one real gap `editorial-light` found in
 * this layer, and it is what `ArtDirection.fonts` below fixes — the registry
 * says which families exist, each art direction says which two it uses.
 *
 * Adding a family is deliberately more than a row here: it also needs a
 * self-hosted `@fontsource` import in `web/src/app/globals.css`, or the name
 * resolves to a system fallback. Two edits is the right amount of friction for
 * a decision that changes every published page.
 *
 * Open licences only, and that is a redistribution rule rather than a taste
 * one: these are served to our customers' audiences, not to visitors of our
 * own site (docs/techstack/frontend.md). */
export const FONT_REGISTRY = {
  fraunces: { family: 'Fraunces', weights: [400, 500, 600] as const },
  inter: { family: 'Inter', weights: [400, 500, 600] as const },
  newsreader: { family: 'Newsreader', weights: [400, 500, 600] as const },
  archivo: { family: 'Archivo', weights: [400, 500, 600] as const },
} as const;

export type FontFamilyId = keyof typeof FONT_REGISTRY;

/** The two slots a type scale may reference. A `TypeRole` picks a slot, an
 * art direction binds each slot to a family — so no role anywhere names a
 * font, and swapping an art direction's whole typography is two ids. */
export type FontSlot = 'display' | 'text';

export type FontWeight = (typeof FONT_REGISTRY)[FontFamilyId]['weights'][number];

export interface TypeRole {
  font: FontSlot;
  size: ClampTriple;
  leading: number; // unitless line-height
  tracking: number; // em
  weight: FontWeight;
  case?: 'uppercase';
  color?: keyof Palette;
}

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

// ---------------------------------------------------------------------------
// Texture — an ordered list of layers, never a bare string. `none` is the
// empty array; there is no separate "off" variant to keep in sync.
//
// `kind` is a closed union of three, and it stays closed: the renderer has one
// implementation per kind and varies only intensity, so a fourth kind is a
// renderer change and therefore a real cost, not a token edit.
// `editorial-light` wants hairline rules rather than glow and takes the empty
// array instead — which is the honest answer for now, and the note for whoever
// finds this vocabulary too small: the gap is real, it was not paid for here.
// ---------------------------------------------------------------------------

export interface TextureLayer {
  kind: 'grain' | 'glow' | 'vignette';
  intensity: number; // 0-1
}

export type Texture = readonly TextureLayer[];

/** How a luminous overlay composites onto the ground.
 *
 * This was `mixBlendMode: 'screen'`, written seven times inside the
 * AbstractVisual generators, and it was correct for exactly as long as every
 * ground was near-black. `screen` keeps only what is lighter than the
 * backdrop, so on white it keeps nothing: phase 11 reviewed those generators
 * over a photograph and fixed them *into* this assumption, and art direction #2
 * is what exposed it — editorial-light's first render showed a gradient mesh as
 * a barely-there smudge on paper.
 *
 * `multiply` is the dual: keep only what is darker. Same generators, same
 * seeds, same shapes; ink instead of light.
 *
 * docs/v1/art-direction.md is explicit about this case — "if a component needs
 * a number the tokens don't provide, the token set has a gap; fill the gap,
 * don't hardcode." The renderer file changed, the renderer's *shape* did not:
 * it reads one more custom property and still branches on nothing. */
export type VisualBlend = 'screen' | 'multiply';

/** How loud the AbstractVisual layer is, 0–1, scaling the generators' own
 * intensity scale rather than replacing it.
 *
 * The second half of the same finding as `VisualBlend`, and it did not become
 * visible until the first was fixed: with `multiply` and cinematic-dark's
 * opacities, editorial-light's oxide red rendered as two large stains across
 * the hero. Which is correct behaviour from the generators — a saturated ink at
 * 45% *is* a stain — and the wrong number for a printed page.
 *
 * The three `intensity` values a scene may ask for (`subtle`/`medium`/`bold`)
 * stay in the renderer, because their *relative* loudness is a property of the
 * schema's enum. How loud the whole layer is, is a property of the art
 * direction, and this is it. */
export type VisualStrength = number;

// ---------------------------------------------------------------------------
// The art direction
// ---------------------------------------------------------------------------

/** The ids that exist. Mirrors `Experience.art_direction` in
 * `api/schema/experience.py`, which is the source of truth — the two are kept
 * in step by hand, and the moment there is a third this should be generated
 * from the schema like everything else that crosses the boundary. */
export type ArtDirectionId = 'cinematic-dark' | 'editorial-light';

export interface ArtDirection {
  id: ArtDirectionId;
  color: Palette;
  fonts: Record<FontSlot, FontFamilyId>;
  type: Record<TypeRoleKey, TypeRole>;
  rhythm: Rhythm;
  texture: Texture;
  visualBlend: VisualBlend;
  visualStrength: VisualStrength;
}
