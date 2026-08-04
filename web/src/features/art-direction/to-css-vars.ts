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
  Length,
  Palette,
  TypeRoleKey,
  Unit,
} from './cinematic-dark';
import { FONT_REGISTRY } from './cinematic-dark';
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

function typeEntries(type: ArtDirection['type']): [string, string][] {
  const fontFamilies: [string, string][] = (
    Object.keys(FONT_REGISTRY) as (keyof typeof FONT_REGISTRY)[]
  ).map((id) => [`--font-${id}`, FONT_REGISTRY[id].family]);

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

function rhythmEntries(rhythm: ArtDirection['rhythm']): [string, string][] {
  return [
    ...rhythm.space.map((s, i): [string, string] => [`--space-${i + 1}`, lengthToCss(s)]),
    ['--scene-padding-y', clampToCss(rhythm.scenePaddingY)],
    ['--scene-padding-x', clampToCss(rhythm.scenePaddingX)],
    ['--measure', lengthToCss(rhythm.measure)],
    ['--content-max', lengthToCss(rhythm.contentMax)],
  ];
}

const TEXTURE_KINDS = ['grain', 'glow', 'vignette'] as const;

function textureEntries(texture: ArtDirection['texture']): [string, string][] {
  return TEXTURE_KINDS.map((kind): [string, string] => {
    const layer = texture.find((l) => l.kind === kind);
    return [`--texture-${kind}-intensity`, String(layer?.intensity ?? 0)];
  });
}

export function toCssVars(ad: ArtDirection): Record<string, string> {
  return Object.fromEntries([
    ...colorEntries(ad.color),
    ...typeEntries(ad.type),
    ...rhythmEntries(ad.rhythm),
    ...textureEntries(ad.texture),
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
  'color' | 'rhythm' | 'texture'
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
  };

  const texture: ArtDirection['texture'] = TEXTURE_KINDS.map((kind) => ({
    kind,
    intensity: Number.parseFloat(requireVar(vars, `--texture-${kind}-intensity`)),
  })).filter((l) => l.intensity > 0);

  return { color, type, rhythm, texture };
}
