// Color math for the token layer. Not lib/ — this is specific to
// art-direction and nothing else needs it yet (docs/coderules/structure.md).
//
// A color is a channel object, never a hex string passed through. That is
// the type decision phase 03 exists to make: "a token whose type is 'any
// string' is a token that will have to be redesigned" — every value that
// crosses this boundary is parsed once, on the way in, and re-serialized on
// the way out (to-css-vars.ts). Nothing downstream ever holds a raw hex.

import { err, ok, type Result } from '@/lib/result';

export interface Color {
  r: number; // 0-255
  g: number; // 0-255
  b: number; // 0-255
  a: number; // 0-1
}

const HEX_RE = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;

/** The one parse, at the boundary where a brand-supplied hex string enters
 * the typed system. Everything past this point is a `Color`, never a string. */
export function parseHex(hex: string): Result<Color> {
  const trimmed = hex.trim();
  const match = HEX_RE.exec(trimmed);
  if (!match) return err('invalid_input', `not a hex color: ${hex}`);

  const digits = match[1];
  if (digits === undefined) return err('invalid_input', `not a hex color: ${hex}`);

  const full =
    digits.length === 3
      ? digits
          .split('')
          .map((c) => c + c)
          .join('')
      : digits;

  const r = Number.parseInt(full.slice(0, 2), 16);
  const g = Number.parseInt(full.slice(2, 4), 16);
  const b = Number.parseInt(full.slice(4, 6), 16);
  return ok({ r, g, b, a: 1 });
}

export function withAlpha(c: Color, a: number): Color {
  return { ...c, a };
}

function srgbToLinear(channel: number): number {
  const c = channel / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

/** WCAG relative luminance. Ignores alpha — callers composite first if the
 * color isn't opaque against its background (see `contrastRatio`). */
export function relativeLuminance(c: Color): number {
  const r = srgbToLinear(c.r);
  const g = srgbToLinear(c.g);
  const b = srgbToLinear(c.b);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function composite(fg: Color, bg: Color): Color {
  return {
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  };
}

/** WCAG contrast ratio between two colors, compositing either over `bg`
 * first if it carries alpha. This is the same formula the phase 02 comps
 * were measured with by hand — codified here so it never drifts. */
export function contrastRatio(a: Color, b: Color, bg: Color): number {
  const la = relativeLuminance(a.a < 1 ? composite(a, bg) : a);
  const lb = relativeLuminance(b.a < 1 ? composite(b, bg) : b);
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);
  return (lighter + 0.05) / (darker + 0.05);
}

function rgbToHsl(c: Color): { h: number; s: number; l: number } {
  const r = c.r / 255;
  const g = c.g / 255;
  const b = c.b / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return { h: 0, s: 0, l };

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h: number;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) * 60;
  else if (max === g) h = ((b - r) / d + 2) * 60;
  else h = ((r - g) / d + 4) * 60;
  return { h, s, l };
}

function hueToRgb(p: number, q: number, t: number): number {
  let tt = t;
  if (tt < 0) tt += 1;
  if (tt > 1) tt -= 1;
  if (tt < 1 / 6) return p + (q - p) * 6 * tt;
  if (tt < 1 / 2) return q;
  if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6;
  return p;
}

function hslToRgb(h: number, s: number, l: number): Color {
  if (s === 0) {
    const v = Math.round(l * 255);
    return { r: v, g: v, b: v, a: 1 };
  }
  const hh = h / 360;
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  return {
    r: Math.round(hueToRgb(p, q, hh + 1 / 3) * 255),
    g: Math.round(hueToRgb(p, q, hh) * 255),
    b: Math.round(hueToRgb(p, q, hh - 1 / 3) * 255),
    a: 1,
  };
}

/** Lighten by `steps` percentage points of HSL lightness, clamped to 100%. */
export function lighten(c: Color, steps: number): Color {
  const { h, s, l } = rgbToHsl(c);
  const next = hslToRgb(h, s, Math.min(1, l + steps / 100));
  return { ...next, a: c.a };
}

/** Darken by `steps` percentage points of HSL lightness, clamped to 0%.
 *
 * The counterpart `lighten` needed once a light art direction existed: on a
 * white ground, a brand colour that fails contrast has to move *away* from
 * white, and lightening it makes it worse until the resolver gives up. See
 * `resolve-brand.ts`. */
export function darken(c: Color, steps: number): Color {
  const { h, s, l } = rgbToHsl(c);
  const next = hslToRgb(h, s, Math.max(0, l - steps / 100));
  return { ...next, a: c.a };
}

export function toCssColor(c: Color): string {
  const r = Math.round(c.r);
  const g = Math.round(c.g);
  const b = Math.round(c.b);
  return c.a >= 1 ? `rgb(${r} ${g} ${b})` : `rgb(${r} ${g} ${b} / ${round(c.a * 100)}%)`;
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}
