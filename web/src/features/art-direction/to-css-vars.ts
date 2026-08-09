// Token object -> CSS custom property bundle, applied at the scene root.
//
// This is the ONLY place a token becomes a string. That single choke point
// is what makes v2's grammar validation (parsing and re-serializing every
// value before it becomes CSS, once users author tokens and the content is
// attacker-supplyable) a change to one file instead of an audit of every
// component that touches a token. docs/v1/art-direction.md.
//
// `fromCssVars` is the inverse and exists to prove the format is lossless —
// the round-trip test is what actually enforces "one place", by failing the
// moment `toCssVars` and `fromCssVars` disagree about the wire format.

import type {
  ArtDirection,
  ClampTriple,
  ColorRole,
  Density,
  FontSlot,
  Layout,
  Length,
  Palette,
  RuleWeight,
  SceneFit,
  ScenePlace,
  Steps,
  TextureLayer,
  TypeRoleKey,
  Unit,
} from './art-direction';
import { COLOR_VAR, FONT_REGISTRY, LAYOUTS } from './art-direction';
import { type Color, toCssColor } from './color';

const TYPE_ROLES: readonly TypeRoleKey[] = [
  'hero',
  'section',
  'lead',
  'normal',
  'muted',
  'eyebrow',
  'stat',
];

function lengthToCss(l: Length): string {
  return `${l.value}${l.unit}`;
}

const LENGTH_RE = /^(-?[\d.]+)([a-z%]+)$/;

function cssToLength(css: string): Length {
  const match = LENGTH_RE.exec(css.trim());
  if (!match) throw new Error(`to-css-vars: not a length: ${css}`);
  const [, value, unit] = match;
  if (value === undefined || unit === undefined) {
    throw new Error(`to-css-vars: not a length: ${css}`);
  }
  return { value: Number.parseFloat(value), unit: unit as Unit };
}

// Always emitted as clamp(), even when all three parts are identical —
// one format, one parser, no branch for the "it happens to be fixed" case.
function clampToCss(c: ClampTriple): string {
  return `clamp(${lengthToCss(c.min)}, ${lengthToCss(c.preferred)}, ${lengthToCss(c.max)})`;
}

const CLAMP_RE = /^clamp\((.+),\s*(.+),\s*(.+)\)$/;

function cssToClamp(css: string): ClampTriple {
  const match = CLAMP_RE.exec(css.trim());
  if (!match) throw new Error(`to-css-vars: not a clamp(): ${css}`);
  const [, min, preferred, max] = match;
  if (min === undefined || preferred === undefined || max === undefined) {
    throw new Error(`to-css-vars: not a clamp(): ${css}`);
  }
  return {
    min: cssToLength(min),
    preferred: cssToLength(preferred),
    max: cssToLength(max),
  };
}

function colorEntries(color: Palette): [string, string][] {
  return [
    ['--bg', toCssColor(color.bg)],
    ['--bg-elevated', toCssColor(color.bgElevated)],
    ['--ink', toCssColor(color.ink)],
    ['--ink-muted', toCssColor(color.inkMuted)],
    ['--ink-faint', toCssColor(color.inkFaint)],
    ['--accent', toCssColor(color.accent)],
    ['--accent-soft', toCssColor(color.accentSoft)],
    ['--veil', toCssColor(color.veil)],
    ['--hairline', toCssColor(color.hairline)],
  ];
}

const FONT_SLOTS: readonly FontSlot[] = ['display', 'text'];

function typeEntries(
  type: ArtDirection['type'],
  fonts: ArtDirection['fonts'],
): [string, string][] {
  // Two variables, one per slot, resolved through the registry — so
  // `--font-display` means "whatever *this* art direction calls display".
  // It used to enumerate the whole registry, which was fine while the registry
  // had exactly the two families the one art direction used, and became wrong
  // the moment a second direction wanted a different pair.
  const fontFamilies: [string, string][] = FONT_SLOTS.map((slot) => [
    `--font-${slot}`,
    FONT_REGISTRY[fonts[slot]].family,
  ]);

  const roles = TYPE_ROLES.flatMap((role): [string, string][] => {
    const def = type[role];
    const entries: [string, string][] = [
      [`--type-${role}-size`, clampToCss(def.size)],
      [`--type-${role}-leading`, String(def.leading)],
      [`--type-${role}-tracking`, `${def.tracking}em`],
      [`--type-${role}-weight`, String(def.weight)],
    ];
    return entries;
  });

  return [...fontFamilies, ...roles];
}

// One variable per layout, so the renderer's read is a *name* lookup keyed by
// something the AI wrote and never a branch on a token's value. The
// `viewport`/`content` decision is resolved here because this is the file whose
// job is turning tokens into strings; resolving it in `scene.tsx` would be a
// second token->string path and the renderer deciding a scene's frame, which
// is what rule 20 forbids.
//
// `auto` rather than `0` for content-height scenes: `min-block-size: auto` is
// the initial value, so the declaration is inert rather than asserting a floor
// of nothing.
//
// The indirection through `--scene-fit-min-block` is what keeps the round trip
// lossless — six `100svh` values cannot tell you the token was `100svh` if
// every layout happens to answer `content`.
function fitEntries(rhythm: ArtDirection['rhythm']): [string, string][] {
  return [
    ['--scene-fit-min-block', lengthToCss(rhythm.fitMinBlock)],
    ...LAYOUTS.map((layout): [string, string] => [
      `--scene-min-block-${layout}`,
      rhythm.fit[layout] === 'viewport' ? 'var(--scene-fit-min-block)' : 'auto',
    ]),
    ['--scene-place', rhythm.fitPlace],
    ['--scene-scroll-margin', lengthToCss(rhythm.fitScrollMargin)],
  ];
}

function rhythmEntries(rhythm: ArtDirection['rhythm']): [string, string][] {
  return [
    ...rhythm.space.map((s, i): [string, string] => [`--space-${i + 1}`, lengthToCss(s)]),
    ['--scene-padding-y', clampToCss(rhythm.scenePaddingY)],
    ['--scene-padding-x', clampToCss(rhythm.scenePaddingX)],
    ['--measure', lengthToCss(rhythm.measure)],
    ['--content-max', lengthToCss(rhythm.contentMax)],
    ...fitEntries(rhythm),
  ];
}

// Texture is emitted **by index**, not by kind. Two layers of the same kind is
// not an edge case here — it is how riso misregistration works (same pattern,
// two token colours, one nudged), so a `--texture-<kind>-*` namespace would
// collide on the one arrangement the vocabulary is built to allow.
//
// Only the fields a kind actually has are emitted. The alternative — a uniform
// ten fields per layer with inert defaults — is 30-plus custom properties on
// every scene root to say almost nothing, and it makes the parse ambiguous
// about which fields were meaningful.
function textureEntries(texture: ArtDirection['texture']): [string, string][] {
  const entries: [string, string][] = [['--texture-count', String(texture.length)]];
  layerEntries(texture, entries, 0);
  return entries;
}

// The image treatment's overlay is a texture layer too, and it is emitted into
// the *same* namespace starting one past the ground layers — so
// `TextureLayerView` reads it with the same variable names and needs no second
// path. It sits outside `--texture-count`, which is the ground list's length
// and is what `fromCssVars` walks.
function imageEntries(
  image: ArtDirection['image'],
  groundLayers: number,
): [string, string][] {
  const entries: [string, string][] = [
    ['--image-edge', lengthToCss(image.edge)],
    ['--image-veil', String(image.veil)],
  ];
  if (image.overlay !== null) layerEntries([image.overlay], entries, groundLayers);
  return entries;
}

function layerEntries(
  texture: ArtDirection['texture'],
  entries: [string, string][],
  offset: number,
): void {
  texture.forEach((layer, n) => {
    const i = n + offset;
    const v = (field: string, value: string): void => {
      entries.push([`--texture-${i}-${field}`, value]);
    };
    v('kind', layer.kind);
    v('opacity', String(layer.intensity));
    v('color', COLOR_VAR[layer.color]);
    v('scale', lengthToCss(layer.scale));
    v('offset', lengthToCss(layer.offset));
    switch (layer.kind) {
      case 'grain':
      case 'weave':
        v('density', String(layer.density));
        break;
      case 'halftone':
        v('angle', `${layer.angle}deg`);
        v('steps', String(layer.steps));
        break;
      case 'hatch':
        v('angle', `${layer.angle}deg`);
        v('cross', layer.cross ? '1' : '0');
        v('density', String(layer.density));
        break;
      case 'dither':
        v('steps', String(layer.steps));
        break;
      case 'rule':
        v('axis', layer.axis);
        v('weight', layer.weight);
        break;
    }
  });
}

/** The brand overlay: the custom properties that change when a brand kit is
 * applied on top of an art direction.
 *
 * **Derived in CSS, not in JavaScript** (docs/v2/plan/01-ad-format.md ->
 * "Derive the palette in CSS"). `--accent-soft` is written as a `color-mix()`
 * against `var(--accent)` rather than computed here, so overriding one variable
 * carries every dependent with it — which is what makes phase 07's reskin a
 * variable swap inside a View Transition rather than a JS pass that has to run
 * between two frames.
 *
 * **The mix ratio comes from the art direction, not from this file.** It is the
 * alpha the direction already declared on its own `accentSoft` token — 12% on
 * `cinematic-dark`, 10% on `editorial-light`, and they mean different things
 * ("a glow" against "a wash behind a pull quote"). Hardcoding either would be
 * this emitter making a decision the token layer already made.
 *
 * OKLCH rather than sRGB for the mix: it is perceptually uniform, so a brand's
 * hue survives the operation instead of drifting the way an HSL or sRGB blend
 * makes it. The contrast correction that produced `accent` still happens in
 * `resolveBrand`, and has to — "lighten until 4.5:1" is a measurement, and CSS
 * cannot measure.
 *
 * `--accent-hover` is in the phase's sketch and is deliberately not emitted:
 * no block reads it. `cta.tsx` uses `var(--accent)` as a background and the
 * artifact has no hover state to token. A token nothing reads is dead weight
 * that looks like coverage — the emitter gains it the day a component needs it.
 */
export function brandCssVars(ad: ArtDirection, accent: Color): Record<string, string> {
  const softness = Math.round(ad.color.accentSoft.a * 100);
  return {
    '--accent': toCssColor(accent),
    '--accent-soft': `color-mix(in oklch, var(--accent) ${String(softness)}%, transparent)`,
  };
}

export function toCssVars(ad: ArtDirection): Record<string, string> {
  return Object.fromEntries([
    ...colorEntries(ad.color),
    ...typeEntries(ad.type, ad.fonts),
    ...rhythmEntries(ad.rhythm),
    ...textureEntries(ad.texture),
    ...imageEntries(ad.image, ad.texture.length),
    ['--visual-blend', ad.visualBlend],
    ['--visual-strength', String(ad.visualStrength)],
  ]);
}

// ---------------------------------------------------------------------------
// The inverse. Round-trip-test support, not a production code path — nothing
// in v1 reads tokens back out of CSS. Kept beside the emitter it inverts so
// the two can never silently drift out of sync with each other.
// ---------------------------------------------------------------------------

function requireVar(vars: Record<string, string>, name: string): string {
  const value = vars[name];
  if (value === undefined) throw new Error(`to-css-vars: missing ${name} in round-trip`);
  return value;
}

// Every one of these is a closed union on the way out, for the reason
// `--visual-blend` already had one: the round trip is only lossless if it
// rejects a value the type does not have rather than widening to `string`.
// Texture is where that matters most now — `glow` and `vignette` were removed
// from the union, and parsing that tolerated an unknown kind is how a removed
// kind survives in stored data and quietly comes back.

const COLOR_ROLE_BY_VAR = new Map<string, ColorRole>(
  (Object.entries(COLOR_VAR) as [ColorRole, string][]).map(([role, v]) => [v, role]),
);

function cssToColorRole(css: string): ColorRole {
  const role = COLOR_ROLE_BY_VAR.get(css.trim());
  if (role === undefined) throw new Error(`to-css-vars: not a colour role: ${css}`);
  return role;
}

function cssToDensity(css: string): Density {
  const n = Number.parseInt(css.trim(), 10);
  if (n !== 1 && n !== 2 && n !== 3 && n !== 4) {
    throw new Error(`to-css-vars: not a density: ${css}`);
  }
  return n;
}

function cssToSteps(css: string): Steps {
  const n = Number.parseInt(css.trim(), 10);
  if (n !== 2 && n !== 3 && n !== 4) {
    throw new Error(`to-css-vars: not a step count: ${css}`);
  }
  return n;
}

function cssToAxis(css: string): 'block' | 'inline' {
  const axis = css.trim();
  if (axis !== 'block' && axis !== 'inline') {
    throw new Error(`to-css-vars: not an axis: ${css}`);
  }
  return axis;
}

function cssToRuleWeight(css: string): RuleWeight {
  const weight = css.trim();
  if (weight !== 'hairline' && weight !== 'thin' && weight !== 'thick') {
    throw new Error(`to-css-vars: not a rule weight: ${css}`);
  }
  return weight;
}

function cssToScenePlace(css: string): ScenePlace {
  const place = css.trim();
  if (place !== 'center' && place !== 'start' && place !== 'end') {
    throw new Error(`to-css-vars: not a scene place: ${css}`);
  }
  return place;
}

function cssToColor(css: string): Color {
  // toCssColor emits "rgb(r g b)" or "rgb(r g b / a%)" — the same subset
  // parseHex's callers never see, so this parses that shape directly rather
  // than pretending it is a hex string.
  const match = /^rgb\((\d+) (\d+) (\d+)(?: \/ ([\d.]+)%)?\)$/.exec(css.trim());
  if (!match) throw new Error(`to-css-vars: not an rgb() color: ${css}`);
  const [, r, g, b, a] = match;
  if (r === undefined || g === undefined || b === undefined) {
    throw new Error(`to-css-vars: not an rgb() color: ${css}`);
  }
  return {
    r: Number.parseInt(r, 10),
    g: Number.parseInt(g, 10),
    b: Number.parseInt(b, 10),
    a: a === undefined ? 1 : Number.parseFloat(a) / 100,
  };
}

export function fromCssVars(vars: Record<string, string>): Pick<
  ArtDirection,
  'color' | 'rhythm' | 'texture' | 'visualBlend' | 'visualStrength'
> & {
  type: Record<
    TypeRoleKey,
    { size: ClampTriple; leading: number; tracking: number; weight: number }
  >;
} {
  const color: Palette = {
    bg: cssToColor(requireVar(vars, '--bg')),
    bgElevated: cssToColor(requireVar(vars, '--bg-elevated')),
    ink: cssToColor(requireVar(vars, '--ink')),
    inkMuted: cssToColor(requireVar(vars, '--ink-muted')),
    inkFaint: cssToColor(requireVar(vars, '--ink-faint')),
    accent: cssToColor(requireVar(vars, '--accent')),
    accentSoft: cssToColor(requireVar(vars, '--accent-soft')),
    veil: cssToColor(requireVar(vars, '--veil')),
    hairline: cssToColor(requireVar(vars, '--hairline')),
  };

  const type = Object.fromEntries(
    TYPE_ROLES.map((role) => [
      role,
      {
        size: cssToClamp(requireVar(vars, `--type-${role}-size`)),
        leading: Number.parseFloat(requireVar(vars, `--type-${role}-leading`)),
        tracking: Number.parseFloat(requireVar(vars, `--type-${role}-tracking`)),
        weight: Number.parseFloat(requireVar(vars, `--type-${role}-weight`)),
      },
    ]),
  ) as Record<
    TypeRoleKey,
    { size: ClampTriple; leading: number; tracking: number; weight: number }
  >;

  const rhythm: ArtDirection['rhythm'] = {
    space: [
      cssToLength(requireVar(vars, '--space-1')),
      cssToLength(requireVar(vars, '--space-2')),
      cssToLength(requireVar(vars, '--space-3')),
      cssToLength(requireVar(vars, '--space-4')),
      cssToLength(requireVar(vars, '--space-5')),
      cssToLength(requireVar(vars, '--space-6')),
      cssToLength(requireVar(vars, '--space-7')),
    ],
    scenePaddingY: cssToClamp(requireVar(vars, '--scene-padding-y')),
    scenePaddingX: cssToClamp(requireVar(vars, '--scene-padding-x')),
    measure: cssToLength(requireVar(vars, '--measure')),
    contentMax: cssToLength(requireVar(vars, '--content-max')),
    fit: Object.fromEntries(
      LAYOUTS.map((layout) => [
        layout,
        requireVar(vars, `--scene-min-block-${layout}`) === 'auto'
          ? 'content'
          : 'viewport',
      ]),
    ) as Record<Layout, SceneFit>,
    fitMinBlock: cssToLength(requireVar(vars, '--scene-fit-min-block')),
    fitPlace: cssToScenePlace(requireVar(vars, '--scene-place')),
    fitScrollMargin: cssToLength(requireVar(vars, '--scene-scroll-margin')),
  };

  const texture: ArtDirection['texture'] = Array.from(
    { length: Number.parseInt(requireVar(vars, '--texture-count'), 10) },
    (_, i): TextureLayer => {
      const f = (field: string): string => requireVar(vars, `--texture-${i}-${field}`);
      const base = {
        intensity: Number.parseFloat(f('opacity')),
        color: cssToColorRole(f('color')),
        scale: cssToLength(f('scale')),
        offset: cssToLength(f('offset')),
      };
      const density = (): Density => cssToDensity(f('density'));
      const steps = (): Steps => cssToSteps(f('steps'));
      const angle = (): number => Number.parseFloat(f('angle'));
      switch (f('kind')) {
        case 'grain':
          return { ...base, kind: 'grain', density: density() };
        case 'weave':
          return { ...base, kind: 'weave', density: density() };
        case 'halftone':
          return { ...base, kind: 'halftone', angle: angle(), steps: steps() };
        case 'hatch':
          return {
            ...base,
            kind: 'hatch',
            angle: angle(),
            cross: f('cross') === '1',
            density: density(),
          };
        case 'dither':
          return { ...base, kind: 'dither', steps: steps() };
        case 'rule':
          return {
            ...base,
            kind: 'rule',
            axis: cssToAxis(f('axis')),
            weight: cssToRuleWeight(f('weight')),
          };
        default:
          throw new Error(`to-css-vars: not a texture kind: ${f('kind')}`);
      }
    },
  );

  // A closed union on the way out too — the round-trip is only lossless if it
  // rejects a value the type does not have, rather than widening to `string`.
  const blend = requireVar(vars, '--visual-blend');
  if (blend !== 'screen' && blend !== 'multiply') {
    throw new Error(`to-css-vars: not a visual blend: ${blend}`);
  }

  return {
    color,
    type,
    rhythm,
    texture,
    visualBlend: blend,
    visualStrength: Number.parseFloat(requireVar(vars, '--visual-strength')),
  };
}
