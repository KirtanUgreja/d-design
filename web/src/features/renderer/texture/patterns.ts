// The shape library. Colourless SVG data URIs, used as `mask-image`; the
// colour underneath always comes from a CSS custom property.
//
// **That split is a security property, not a style preference.** A data-URI
// SVG cannot resolve `var()`, so the only way to give a pattern a colour
// directly is to interpolate a token value into a URI-encoded string — which
// is exactly the pass-a-token-through-as-a-string that v2 rule 13 forbids, in
// about the least visible place in the codebase. Masking makes the correct
// thing the easy thing: there are no colours in this file, and a pattern that
// wanted one could not have it. `to-css-vars.ts` stays the only token->string
// path.
//
// **No `fill` attribute anywhere below, deliberately.** SVG's default fill is
// opaque black, and a CSS mask sourced from an image uses its *alpha*, so
// "opaque" means "show the colour underneath". Writing `fill="white"` would
// mean the same thing and would put a colour word in a file whose whole claim
// is that it has none. docs/v2/plan/14-texture-without-gradient.md.
//
// Everything here is a *tile*, sized at use with `mask-size` from the art
// direction's `scale` token, and rotated (where a kind has an angle) by
// rotating an oversized element rather than the tile — a square tile repeated
// at an arbitrary angle seams, an oversized rotated element does not.

const svg = (width: number, height: number, body: string): string =>
  `url("data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">${body}</svg>`,
  )}")`;

/** How much of a tile the mark covers. Not an opacity and not a token — it is
 * the structural knob a *stepped* kind moves between bands, which is what
 * keeps banding discrete instead of becoming a ramp with extra steps. */
export type Density = 1 | 2 | 3 | 4;

// --- halftone ---------------------------------------------------------------

/** One dot per 16x16 tile. The radii are spaced so that consecutive densities
 * are obviously different at a glance — a halftone whose bands differ by a few
 * percent is a gradient someone quantised, which is the failure this whole
 * vocabulary exists to avoid. */
const HALFTONE_RADIUS: Record<Density, number> = { 1: 1.1, 2: 2.1, 3: 3.2, 4: 4.4 };

export const halftone = (density: Density): string =>
  svg(16, 16, `<circle cx="8" cy="8" r="${HALFTONE_RADIUS[density]}"/>`);

// --- dither -----------------------------------------------------------------

/** The ordered Bayer 4x4 matrix. A cell is on when its threshold is below the
 * level, so levels nest: every cell lit at level 4 is lit at level 8. That
 * nesting is why bands have to be drawn as non-overlapping rings rather than
 * stacked — overlapping two levels of a nested pattern yields the denser of
 * the two everywhere, which is a flat field, not a dissolve. */
const BAYER = [
  [0, 8, 2, 10],
  [12, 4, 14, 6],
  [3, 11, 1, 9],
  [15, 7, 13, 5],
];

/** `level` is 1..15 — the number of the 16 cells that are lit. */
export const dither = (level: number): string => {
  const cells: string[] = [];
  for (let y = 0; y < 4; y++) {
    for (let x = 0; x < 4; x++) {
      const row = BAYER[y];
      const threshold = row?.[x];
      if (threshold !== undefined && threshold < level) {
        cells.push(`<rect x="${x}" y="${y}" width="1" height="1"/>`);
      }
    }
  }
  return svg(4, 4, cells.join(''));
};

/** Four levels evenly spread across the matrix, so a `steps: 4` dissolve uses
 * the whole range rather than four values that all look alike. */
export const DITHER_LEVEL: Record<Density, number> = { 1: 2, 2: 5, 3: 9, 4: 13 };

// --- hatch ------------------------------------------------------------------

/** Parallel engraved rules. `cross` adds the perpendicular set, which reads as
 * cross-hatch rather than as a grid because the lines are thin relative to the
 * tile. The angle is applied by the layer, not baked here. */
export const hatch = (density: Density, cross: boolean): string => {
  const weight = density * 0.5;
  const lines = [`<rect x="0" y="0" width="8" height="${weight}"/>`];
  if (cross) lines.push(`<rect x="0" y="0" width="${weight}" height="8"/>`);
  return svg(8, 8, lines.join(''));
};

// --- weave ------------------------------------------------------------------

/** Canvas, uncoated stock. Two interleaved runs offset by half a tile — the
 * quietest kind in the vocabulary, and the one that reads on white, which is
 * the property the three v1 kinds all lacked. */
export const weave = (density: Density): string => {
  const w = 2 + density;
  return svg(
    8,
    8,
    `<rect x="0" y="0" width="${w}" height="4"/><rect x="4" y="4" width="${w}" height="4"/>`,
  );
};

// --- rule -------------------------------------------------------------------

/** Hairline structural rules along one axis. Promoted from `editorial-light`
 * taking the empty array into a real answer.
 *
 * `weight` is a three-value enum rather than a `Length`, and that is a
 * deviation from the phase doc worth knowing: a tile baked into a data URI
 * cannot read a token, so a `Length` here would have to be interpolated into
 * the URI — the one thing this file exists to prevent. Three named weights
 * select three tiles; the token stays typed and nothing is stringified. */
export type RuleWeight = 'hairline' | 'thin' | 'thick';

const RULE_WEIGHT: Record<RuleWeight, number> = { hairline: 0.5, thin: 1, thick: 2 };

export const rule = (axis: 'block' | 'inline', weight: RuleWeight): string => {
  const w = RULE_WEIGHT[weight];
  return axis === 'block'
    ? svg(16, 16, `<rect x="0" y="0" width="16" height="${w}"/>`)
    : svg(16, 16, `<rect x="0" y="0" width="${w}" height="16"/>`);
};

// --- grain ------------------------------------------------------------------

/** Film emulsion and paper tooth. The one kind carried over from v1 unchanged
 * in character — but it is a *mask* now rather than a painted layer, so its
 * colour comes from a token like every other kind instead of being whatever
 * `feTurbulence` happens to emit.
 *
 * The `#g` below is the only `#` in this file and it is a filter fragment
 * reference, not a colour. `svg()` runs the whole document through
 * `encodeURIComponent`, so it reaches the browser as `%23g` — writing `%23`
 * here directly would be double-encoded and the filter would silently not
 * apply, leaving a flat rectangle that looks like a very bold grain. */
export const grain = (density: Density): string =>
  svg(
    64,
    64,
    `<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="${(0.5 + density * 0.2).toFixed(2)}" numOctaves="2" stitchTiles="stitch"/></filter><rect width="64" height="64" filter="url(#g)"/>`,
  );
