// Brand colors map into semantic roles, they do not replace them.
// `cinematic-dark` stays dark under a pastel brand — it applies the brand's
// accent to a dark system rather than adopting the brand wholesale. A
// marketer choosing a cinematic art direction is choosing cinematic.
// docs/v1/art-direction.md -> "Brand kit integration"

import type { BrandKit } from '@/schema';
import { err, ok, type Result } from '@/lib/result';

import type { ArtDirection } from './art-direction';
import {
  contrastRatio,
  darken,
  lighten,
  parseHex,
  relativeLuminance,
  type Color,
} from './color';

const MIN_CONTRAST = 4.5;
const STEP = 4; // HSL lightness percentage points per attempt
const MAX_ATTEMPTS = 20; // 20 * 4 = 80 points of headroom; if that isn't enough, nothing is

/** Which way is "away from the ground".
 *
 * This function is what `editorial-light` cost this file. The resolver only
 * ever lightened, which is correct on a near-black ground and exactly backwards
 * on a near-white one: a brand red that fails against white gets *lighter*,
 * fails harder, and twenty attempts later the resolver reports that the colour
 * cannot reach 4.5:1 — a false negative that would have rejected perfectly
 * usable brand colours on every light art direction.
 *
 * The threshold is the ground's own luminance, not a hardcoded "is this
 * direction dark": an art direction with a mid-grey ground picks whichever
 * direction has more room, which is the right answer without anyone declaring
 * a polarity token. 0.18 rather than 0.5 because luminance is not perceptual
 * lightness — a "mid grey" ground sits around 0.2. */
function awayFromGround(bg: Color): (c: Color, steps: number) => Color {
  return relativeLuminance(bg) > 0.18 ? darken : lighten;
}

export interface ResolvedPalette {
  /** The brand's primary, corrected until it clears 4.5:1 against the ground.
   * Text-safe by construction. */
  accent: Color;
  /** The brand's own primary, unmodified. Non-text surfaces only — a fill, a
   * glow source — never text, which is exactly why `accent` above exists as
   * the corrected value and this exists alongside it rather than in place of it. */
  accentRaw: Color;
}

/**
 * Contrast is enforced, not hoped for. If `brand.primary` fails 4.5:1
 * against `--bg`, move it away from the ground until it passes and keep the
 * original for non-text surfaces only. A brand color that cannot reach 4.5:1
 * returns a `Result` failure rather than a best effort — anything that could
 * ship unreadable text fails closed (docs/coderules/patterns.md rule 5).
 *
 * **Two values, not a palette.** This used to return the whole `Palette` with
 * one field replaced, which was a palette derived in JavaScript — and it had a
 * bug hiding in it: `accentSoft` came through as the art direction's own, so a
 * brand applied to `cinematic-dark` got amber wash under a red accent. What
 * JavaScript has to do here is the *measurement*, because "move it until it
 * clears 4.5:1" cannot be expressed in CSS. Everything downstream of the
 * corrected value is a derivation, and derivations belong in `brandCssVars`.
 */
export function resolveBrand(brand: BrandKit, ad: ArtDirection): Result<ResolvedPalette> {
  const parsed = parseHex(brand.primary);
  if (!parsed.ok) return err('invalid_input', `brand.primary: ${parsed.error.message}`);

  const raw = parsed.value;
  const away = awayFromGround(ad.color.bg);
  let candidate = raw;
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    if (contrastRatio(candidate, ad.color.bg, ad.color.bg) >= MIN_CONTRAST) {
      return ok({ accent: candidate, accentRaw: raw });
    }
    candidate = away(raw, STEP * (attempt + 1));
  }

  return err(
    'invalid_input',
    `brand.primary (${brand.primary}) cannot reach ${MIN_CONTRAST}:1 against ${ad.id}'s --bg`,
  );
}
