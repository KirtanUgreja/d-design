// Brand colors map into semantic roles, they do not replace them.
// `cinematic-dark` stays dark under a pastel brand — it applies the brand's
// accent to a dark system rather than adopting the brand wholesale. A
// marketer choosing a cinematic art direction is choosing cinematic.
// docs/v1/art-direction.md -> "Brand kit integration"

import type { BrandKit } from '@/schema';
import { err, ok, type Result } from '@/lib/result';

import type { ArtDirection, Palette } from './cinematic-dark';
import { contrastRatio, lighten, parseHex } from './color';

const MIN_CONTRAST = 4.5;
const LIGHTEN_STEP = 4; // HSL lightness percentage points per attempt
const MAX_ATTEMPTS = 20; // 20 * 4 = 80 points of headroom; if that isn't enough, nothing is

export interface ResolvedPalette extends Palette {
  /** The brand's own primary, unmodified. Non-text surfaces only — a fill, a
   * glow source — never text, which is exactly why `accent` above exists as
   * the corrected value and this exists alongside it rather than in place of it. */
  accentRaw: Palette['accent'];
}

/**
 * Contrast is enforced, not hoped for. If `brand.primary` fails 4.5:1
 * against `--bg`, lighten it until it passes and keep the original for
 * non-text surfaces only. A brand color that cannot reach 4.5:1 by
 * lightening returns a `Result` failure rather than a best effort —
 * anything that could ship unreadable text fails closed
 * (docs/coderules/patterns.md rule 5).
 */
export function resolveBrand(brand: BrandKit, ad: ArtDirection): Result<ResolvedPalette> {
  const parsed = parseHex(brand.primary);
  if (!parsed.ok) return err('invalid_input', `brand.primary: ${parsed.error.message}`);

  const raw = parsed.value;
  let candidate = raw;
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    if (contrastRatio(candidate, ad.color.bg, ad.color.bg) >= MIN_CONTRAST) {
      return ok({ ...ad.color, accent: candidate, accentRaw: raw });
    }
    candidate = lighten(raw, LIGHTEN_STEP * (attempt + 1));
  }

  return err(
    'invalid_input',
    `brand.primary (${brand.primary}) cannot reach ${MIN_CONTRAST}:1 against --bg by lightening`,
  );
}
