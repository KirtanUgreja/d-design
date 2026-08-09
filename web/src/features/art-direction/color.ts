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

// ---------------------------------------------------------------------------
// APCA
//
// **APCA-W3 revision 0.1.9 (beta, 2022-07-03), constants from `SA98G`** — the
// same revision `api/features/art_direction/lint_contrast.py` pins, because two
// implementations of a moving draft are only one implementation if they name
// the same revision. `art-direction.test.ts` and `test_lint.py` share a fixture
// table that fails if the two ever disagree, which is the treatment
// `contrastRatio` already has for the same reason.
//
// **Why this is duplicated at all**, rather than `resolveBrand` asking `api`:
// this runs inside the renderer, which is pure and synchronous and runs in three
// processes (rule 6). A brand correction that needs a network round trip is a
// brand correction that fails when `api` is slow, and "fails" there means either
// a page with no accent or a page with an unchecked one.
//
// It exists because `resolveBrand` corrects until a colour passes, and until v2
// phase 04 the only thing it could measure was WCAG 2 — so it corrected a brand
// colour until the polarity-blind standard was satisfied and then stopped, on
// art directions whose entire premise is a dark ground. Rule 14 says both gates
// are hard failures; a resolver that could only see one of them was enforcing
// half of it.
const MAIN_TRC = 2.4;
const RCO = 0.2126729;
const GCO = 0.7151522;
const BCO = 0.072175;
const NORM_BG = 0.56;
const NORM_TXT = 0.57;
const REV_TXT = 0.62;
const REV_BG = 0.65;
const BLK_THRS = 0.022;
const BLK_CLMP = 1.414;
const SCALE_BOW = 1.14;
const SCALE_WOB = 1.14;
const LO_BOW_OFFSET = 0.027;
const LO_WOB_OFFSET = 0.027;
const DELTA_Y_MIN = 0.0005;
const LO_CLIP = 0.1;

/** APCA uses a simple 2.4 power curve, not the piecewise sRGB one above. That
 * is not an approximation of `srgbToLinear` — it is a different transfer
 * function, and mixing them up is the classic way to get an APCA
 * implementation that is subtly wrong everywhere. */
function apcaY(c: Color): number {
  return (
    RCO * (c.r / 255) ** MAIN_TRC +
    GCO * (c.g / 255) ** MAIN_TRC +
    BCO * (c.b / 255) ** MAIN_TRC
  );
}

/** The soft clamp near black, and the reason APCA can judge a dark art
 * direction when WCAG 2 structurally cannot: WCAG's ratio is dominated by its
 * `+0.05` term down there, which is what makes every near-black ground score
 * alike. */
function softClamp(y: number): number {
  return y > BLK_THRS ? y : y + (BLK_THRS - y) ** BLK_CLMP;
}

/** Lightness contrast `Lc`, signed by polarity: positive is dark text on a
 * light ground, negative is light text on a dark one. Callers compare the
 * absolute value — the threshold is about legibility and the sign is about
 * which way round the design is — but the sign is returned rather than
 * discarded, because throwing it away makes a polarity-aware metric behave like
 * a polarity-blind one. */
export function apcaLc(text: Color, background: Color): number {
  const textY = softClamp(apcaY(text.a < 1 ? composite(text, background) : text));
  const bgY = softClamp(
    apcaY(background.a < 1 ? composite(background, background) : background),
  );

  if (Math.abs(bgY - textY) < DELTA_Y_MIN) return 0;

  if (bgY > textY) {
    const sapc = (bgY ** NORM_BG - textY ** NORM_TXT) * SCALE_BOW;
    return (sapc < LO_CLIP ? 0 : sapc - LO_BOW_OFFSET) * 100;
  }
  const sapc = (bgY ** REV_BG - textY ** REV_TXT) * SCALE_WOB;
  return (sapc > -LO_CLIP ? 0 : sapc + LO_WOB_OFFSET) * 100;
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
