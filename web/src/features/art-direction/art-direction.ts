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

import type { Block, Scene } from '@/schema';

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

// `svh` is the *small* viewport height — the one measured with the mobile
// browser chrome expanded. It is here rather than `vh` or `dvh` because a
// scene is a stage, and a stage that resizes while the audience is looking at
// it is not one: `vh` is the largest viewport and overflows by the height of
// the URL bar on first paint, and `dvh` is correct at every instant and
// therefore recalculates at every instant, moving snap points mid-scroll.
// docs/v2/plan/13-scene-fit.md -> "100svh, and specifically not vh or dvh".
//
// ponytail: no `vh` fallback declaration before the `svh` one. The phase asked
// for both so an engine that does not know the unit still gets a floor, and a
// React inline style cannot carry a duplicate property — the ceiling is that a
// browser predating 2023 gets no floor at all. Upgrade path: move the fit
// shell's declarations to a stylesheet, where two can be written.
export type Unit = 'px' | 'rem' | 'ch' | 'vw' | 'vh' | 'svh' | '%';

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
export const svh = (value: number): Length => ({ value, unit: 'svh' });

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
 * `weights` is **what we self-host, not what the family ships.** Syne publishes
 * 400-800 and Space Grotesk 300-700; the rows below carry the weights an art
 * direction actually authors, because every entry here is a file every reader
 * of every published page downloads. Wanting one more is a deliberate two-line
 * change and not an accident.
 *
 * Open licences only, and that is a redistribution rule rather than a taste
 * one: these are served to our customers' audiences, not to visitors of our
 * own site (docs/techstack/frontend.md). All six are OFL-1.1. */
export const FONT_REGISTRY = {
  fraunces: { family: 'Fraunces', weights: [400, 500, 600] as const },
  inter: { family: 'Inter', weights: [400, 500, 600] as const },
  newsreader: { family: 'Newsreader', weights: [400, 500, 600] as const },
  archivo: { family: 'Archivo', weights: [400, 500, 600] as const },
  // `bold-brutalist`, and the reason the four rows above stopped being able to
  // share one weight list. Syne is the only registered family that self-hosts
  // above 600 — `clamp(4rem, 12vw, 14rem)` at 500 is not a brutalist headline,
  // it is a large thin one — and 800 is the only weight it is asked for.
  syne: { family: 'Syne', weights: [800] as const },
  'space-grotesk': { family: 'Space Grotesk', weights: [400, 500, 700] as const },
} as const;

export type FontFamilyId = keyof typeof FONT_REGISTRY;

/** The weights one family self-hosts. A `readonly number[]` rather than the
 * family's own literal tuple, because callers hold a `FontFamilyId` that is not
 * statically known — the family comes from a database row. */
export function registeredWeights(id: FontFamilyId): readonly number[] {
  return FONT_REGISTRY[id].weights;
}

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

// ---------------------------------------------------------------------------
// Scene fit — whether a scene owns the frame.
//
// The tempting shape is a `fit` field on `Scene`, and it is the wrong one: how
// much of the frame a scene occupies is a presentational decision, and rule 7
// says the AI does not get one. It is also wrong for reskin — a scene the model
// pinned to `viewport` would stay pinned under an art direction whose whole
// character is that proof scenes run long.
//
// So the art direction owns a lookup from something the AI *does* write. The AI
// writes `layout`; the art direction turns that into a frame; nothing new
// reaches the schema. `cinematic-dark` answers `viewport` for all six —
// deep space, one beat per screen. `editorial-light` answers `content` for
// `stack` and `grid`, because a printed spread that pads a spec table to full
// height looks like a spec table with a bug. Two answers, one code path.
//
// docs/v2/plan/13-scene-fit.md, and rule 20 in docs/v2/plan/README.md.
// ---------------------------------------------------------------------------

/** The layout vocabulary the AI writes, derived from the schema rather than
 * re-typed — `renderer/layouts/region.ts` re-exports this rather than
 * declaring a second copy. */
export type Layout = Scene['layout'];

/** The same union as a value, for the places that have to iterate it — the
 * emitter and its tests. Typed as `readonly Layout[]` so dropping an entry is
 * caught the moment anything builds a `Record<Layout, …>` from it. */
export const LAYOUTS: readonly Layout[] = [
  'full-bleed',
  'split-left',
  'split-right',
  'centered',
  'stack',
  'grid',
];

export type SceneFit = 'viewport' | 'content';

/** Block-axis placement of a scene's content within its frame. A four-word
 * hero in a full-height box placed at `start` is a headline stuck to the
 * ceiling of an empty room; half the perceived quality of the fit shell is
 * this token being `center`. It is a token and not a constant because
 * `bold-brutalist` will want `end` — type jammed to the baseline is most of
 * what that art direction is. */
export type ScenePlace = 'center' | 'start' | 'end';

export interface Rhythm {
  space: readonly [Length, Length, Length, Length, Length, Length, Length];
  scenePaddingY: ClampTriple;
  scenePaddingX: ClampTriple;
  measure: Length;
  contentMax: Length;
  fit: Record<Layout, SceneFit>;
  /** The floor a `viewport` scene gets — a floor, never a fixed height. A
   * scene with more content than the frame grows and is reported; it is never
   * clipped and never scrolls inside itself. Kept a token rather than a
   * constant because an art direction that wants 90svh, with a deliberate
   * sliver of the next scene showing, is making a legitimate choice. */
  fitMinBlock: Length;
  fitPlace: ScenePlace;
  /** Clears the fixed present/motion control pill, which sits at the top of
   * the same viewport `scrollIntoView` and scroll-snap align against. Without
   * it the first line of every scene reached by arrow key lands underneath the
   * chrome. A token because the chrome's height is not the renderer's
   * business. */
  fitScrollMargin: Length;
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

/** A palette entry by name. A texture layer references a colour, it never
 * carries one — which is what lets the pattern itself be a colourless mask
 * (`renderer/texture/patterns.ts`) and keeps rule 13 intact. */
export type ColorRole = keyof Palette;

/** Role -> the custom property `to-css-vars.ts` emits it as. Canonical here
 * rather than in `renderer/tokens.ts`, which re-exports it: the emitter and
 * the renderer have to agree on these names, and two copies of an agreement
 * is the shape of a drift. */
export const COLOR_VAR: Record<ColorRole, string> = {
  bg: 'var(--bg)',
  bgElevated: 'var(--bg-elevated)',
  ink: 'var(--ink)',
  inkMuted: 'var(--ink-muted)',
  inkFaint: 'var(--ink-faint)',
  accent: 'var(--accent)',
  accentSoft: 'var(--accent-soft)',
  veil: 'var(--veil)',
  hairline: 'var(--hairline)',
};

/** How dense a mark is within its tile. Structural, not a token value: it is
 * the knob a *stepped* kind moves between bands. */
export type Density = 1 | 2 | 3 | 4;

/** 2 to 4 discrete bands with hard boundaries. The aesthetic rule that keeps
 * the vocabulary honest — a halftone that fades by continuously shrinking its
 * dots is a gradient with extra work. */
export type Steps = 2 | 3 | 4;

export type RuleWeight = 'hairline' | 'thin' | 'thick';

interface TextureBase {
  intensity: number; // 0-1
  color: ColorRole;
  /** Tile size. Every kind interprets it — dot pitch, hatch spacing, rule
   * spacing. The phase doc gives `rule` no scale; it needs one, because
   * spacing has to come from somewhere and a constant here would be our
   * choice for every art direction. */
  scale: Length;
  /** Riso misregistration. Two layers of the same kind in two token colours,
   * one of them nudged, composited with the AD's `visualBlend` — colour,
   * texture and depth out of the layer list with no third mechanism. `px(0)`
   * is no offset, which is what every layer that is not half of a riso pair
   * uses. */
  offset: Length;
}

export type TextureLayer =
  | (TextureBase & { kind: 'grain'; density: Density })
  | (TextureBase & { kind: 'halftone'; angle: number; steps: Steps })
  | (TextureBase & { kind: 'hatch'; angle: number; cross: boolean; density: Density })
  | (TextureBase & { kind: 'dither'; steps: Steps })
  | (TextureBase & { kind: 'weave'; density: Density })
  | (TextureBase & { kind: 'rule'; axis: 'block' | 'inline'; weight: RuleWeight });

export type Texture = readonly TextureLayer[];

// ---------------------------------------------------------------------------
// Image treatment — the art direction consuming a photograph.
//
// The same principle as brand colour: "brand colours map into semantic roles,
// they do not replace them" (docs/v1/art-direction.md), applied to pixels. An
// uploaded photograph arrives with its own colour, contrast and light. Dropped
// into `cinematic-dark` untreated it reads as a stock image *on* a dark page
// rather than part of one.
//
// This is also where the reskin claim gets its best demonstration: one
// photograph, three art directions, three visibly different images, with no
// re-encode and no second asset row — because the treatment is a token and the
// pixels never changed. docs/v2/plan/15-images.md.
// ---------------------------------------------------------------------------

export type ImageTone = 'as-shot' | 'mono' | 'duotone' | 'posterize';
export type ImageFrame = 'none' | 'hairline' | 'block' | 'inset';

/** A crop this art direction will accept, as `width / height`. An art
 * direction that accepts any ratio has no compositional opinion; cropping to a
 * declared set is what makes a page of images read as a spread rather than a
 * folder. Applied with `object-fit: cover` against a token `aspect-ratio`,
 * never by re-encoding — so switching art directions re-crops instead of
 * reprocessing. */
export interface Ratio {
  w: number;
  h: number;
}

export interface ImageTreatment {
  tone: ImageTone;
  /** Composited over the photograph from phase 14's vocabulary, so an image
   * carries the same surface as the ground it sits on. `null` is none. */
  overlay: TextureLayer | null;
  frame: ImageFrame;
  /** Corner radius. Zero for most art directions — a rounded photograph is a
   * UI card, and this product makes pages. */
  edge: Length;
  /** 0–1. A flat scrim for text over media. Flat, because the conventional
   * bottom-up scrim is a gradient and rule 18 does not have an exception for
   * the case everyone makes an exception for. */
  veil: number;
  ratios: readonly Ratio[];
}

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
// Brand mapping — how this art direction consumes a brand kit, never the
// reverse. A marketer choosing an art direction is choosing that art direction.
//
// Stored since v2 phase 01 and **read by nothing until phase 04**, which is why
// it is on `ArtDirection` only now: `cinematic-dark` and `editorial-light` both
// take every default, so the whole group was indistinguishable from the
// hardcoded behaviour `resolveBrand` already had. `bold-brutalist` is the first
// art direction to disagree with a default, and disagreeing is what turns a
// stored field into a read one.
// ---------------------------------------------------------------------------

/** Where `brand.primary` lands. `accent` and `ink` are foreground roles and are
 * corrected against the ground; `bg` replaces the ground itself and is the one
 * that needs `allowBrandBackground`. */
export type AccentRole = 'accent' | 'bg' | 'ink';

/** Which way "away from the ground" is, when a brand colour has to move to
 * clear contrast. `auto` computes it from the ground's own luminance, which is
 * what v1 found to be better than an art direction asserting one — the explicit
 * values exist for a ground whose luminance sits near the crossover, where the
 * computation has no good answer and the designer does. */
export type ContrastStrategy = 'lighten' | 'darken' | 'auto';

export interface BrandMapping {
  accentRole: AccentRole;
  /** May the brand colour become the page ground? False everywhere except
   * `bold-brutalist`, and this field exists because of that one art direction —
   * a brand colour behind a full-bleed hero is not a setting, it is a different
   * design. */
  allowBrandBackground: boolean;
  logoTreatment: 'mono' | 'full-color';
  contrastStrategy: ContrastStrategy;
}

// ---------------------------------------------------------------------------
// The art direction
// ---------------------------------------------------------------------------

export interface ArtDirection {
  /** Which art direction this is, for messages and dev harnesses — never a
   * branch. It was a two-value union until v2 phase 01, which made a missing
   * art direction a compile error and had nowhere to put a version; art
   * directions are rows now, so the identity that matters is `ArtDirectionRef`
   * (`{id, version}`) and it is checked against the store rather than by the
   * compiler. `docs/v2/plan/01-ad-format.md` -> "`resolveArtDirection` stops
   * being a code table" is explicit that losing the compile-time check
   * deliberately beats pretending it survived a database read. */
  id: string;
  color: Palette;
  fonts: Record<FontSlot, FontFamilyId>;
  type: Record<TypeRoleKey, TypeRole>;
  rhythm: Rhythm;
  texture: Texture;
  image: ImageTreatment;
  visualBlend: VisualBlend;
  visualStrength: VisualStrength;
  brandMapping: BrandMapping;
}
