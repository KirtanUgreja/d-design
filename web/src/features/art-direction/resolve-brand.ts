// Brand colors map into semantic roles, they do not replace them.
// `cinematic-dark` stays dark under a pastel brand — it applies the brand's
// accent to a dark system rather than adopting the brand wholesale. A
// marketer choosing a cinematic art direction is choosing cinematic.
// docs/v1/art-direction.md -> "Brand kit integration"
//
// **`bold-brutalist` is the exception the rule is written to survive**, and it
// is why `BrandMapping` stopped being a stored-but-unread field in v2 phase 04.
// That art direction's whole premise is that your colour becomes the page, so
// `accentRole: 'bg'` moves the brand to the ground at full strength and nothing
// corrects it. The correction moves to the other side of the pair: what has to
// be checked is whether the art direction's own ink still reads on a ground it
// has never seen. It is the same rule — nobody ships unreadable text — pointed
// the other way.

import type { BrandKit } from '@/schema';
import { err, ok, type Result } from '@/lib/result';

import type { ArtDirection, ContrastStrategy } from './art-direction';
import {
  apcaLc,
  contrastRatio,
  darken,
  lighten,
  parseHex,
  relativeLuminance,
  type Color,
} from './color';

const MIN_CONTRAST = 4.5;
/** APCA body text. The same Lc 75 the linter applies, and applied here for the
 * same reason rule 14 gives: WCAG 2.2 is the legal floor and APCA is the gate
 * that can tell whether a dark art direction is actually readable. Until phase
 * 04 this resolver measured only the first of those, so it corrected a brand
 * colour until a polarity-blind standard was satisfied and then stopped — on
 * art directions whose entire premise is a dark ground. */
const MIN_LC = 75;
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
 * lightness — a "mid grey" ground sits around 0.2.
 *
 * **`contrastStrategy` overrides it, and that is the field's only reader.** The
 * computation above is better than a declaration for almost every ground, which
 * is why `auto` is what all three shipped art directions choose. It is worse for
 * exactly one case: a ground sitting near the 0.18 crossover, where "whichever
 * has more room" is a coin toss between two answers that look nothing alike.
 * There the designer knows and the luminance does not. */
function correction(
  bg: Color,
  strategy: ContrastStrategy,
): (c: Color, n: number) => Color {
  if (strategy === 'lighten') return lighten;
  if (strategy === 'darken') return darken;
  return relativeLuminance(bg) > 0.18 ? darken : lighten;
}

/** Both gates, in the order their failures should be reported. */
function passes(fg: Color, bg: Color): boolean {
  return contrastRatio(fg, bg, bg) >= MIN_CONTRAST && Math.abs(apcaLc(fg, bg)) >= MIN_LC;
}

export interface ResolvedPalette {
  /** The brand's primary, corrected until it clears both gates against the
   * ground. Text-safe by construction. Null when this art direction puts the
   * brand somewhere that is not a foreground — see `ground`. */
  accent: Color | null;
  /** The brand's own primary, unmodified. Non-text surfaces only — a fill, a
   * block — never text, which is exactly why `accent` above exists as the
   * corrected value and this exists alongside it rather than in place of it. */
  accentRaw: Color;
  /** The brand as the page's ground, uncorrected. Non-null only for an art
   * direction with `accentRole: 'bg'` and `allowBrandBackground`, which today
   * is `bold-brutalist` alone.
   *
   * Uncorrected on purpose: a corrected brand ground is a brand colour this
   * art direction decided it knew better than, and "your colour at full
   * strength" is the entire offer. The check that replaces the correction is
   * the refusal below. */
  ground: Color | null;
}

/**
 * Contrast is enforced, not hoped for, in whichever direction this art
 * direction's `brandMapping` points.
 *
 * **The brand lands on a foreground role** (`accent`, `ink`): if it fails
 * against `--bg`, move it away from the ground until it clears both gates and
 * keep the original for non-text surfaces only. A brand color that cannot get
 * there returns a `Result` failure rather than a best effort — anything that
 * could ship unreadable text fails closed (docs/coderules/patterns.md rule 5).
 *
 * **The brand becomes the ground** (`bg`): nothing is corrected, and the art
 * direction's own `ink` and CTA fill are measured against it instead. A brand
 * colour too dark for near-black type is refused, with a message written for
 * the person who chose the colour rather than for the person who wrote this.
 *
 * **Two values, not a palette.** This used to return the whole `Palette` with
 * one field replaced, which was a palette derived in JavaScript — and it had a
 * bug hiding in it: `accentSoft` came through as the art direction's own, so a
 * brand applied to `cinematic-dark` got amber wash under a red accent. What
 * JavaScript has to do here is the *measurement*, because "move it until it
 * clears both gates" cannot be expressed in CSS. Everything downstream of the
 * measured value is a derivation, and derivations belong in `brandCssVars`.
 */
export function resolveBrand(brand: BrandKit, ad: ArtDirection): Result<ResolvedPalette> {
  const parsed = parseHex(brand.primary);
  if (!parsed.ok) return err('invalid_input', `brand.primary: ${parsed.error.message}`);

  const raw = parsed.value;
  const { accentRole, allowBrandBackground, contrastStrategy } = ad.brandMapping;

  if (accentRole === 'bg') {
    // A record that asks for a brand ground without allowing one is a
    // contradiction, and the linter refuses it at save (`BRAND_BACKGROUND_NOT_
    // ALLOWED`). Reaching it here means a row got in another way, so it fails
    // closed rather than picking one of the two halves to believe.
    if (!allowBrandBackground) {
      return err(
        'invalid_input',
        `${ad.id}: accentRole is 'bg' but allowBrandBackground is false`,
      );
    }
    return resolveGround(raw, brand.primary, ad);
  }

  const against = ad.color.bg;
  const away = correction(against, contrastStrategy);
  let candidate = raw;
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    if (passes(candidate, against)) {
      return ok({ accent: candidate, accentRaw: raw, ground: null });
    }
    candidate = away(raw, STEP * (attempt + 1));
  }

  return err(
    'invalid_input',
    `brand.primary (${brand.primary}) cannot reach ${String(MIN_CONTRAST)}:1 and ` +
      `Lc ${String(MIN_LC)} against ${ad.id}'s --bg`,
  );
}

/** The brand as the ground, and the two pairs that decides.
 *
 * Both are pairs the art direction already had — its ink on its ground, and its
 * CTA label on its accent fill — with the ground swapped underneath them. The
 * second is the one that is easy to forget and the one that matters most: a CTA
 * label is `bg`-coloured text, so when `bg` becomes the brand, the most
 * important text on the page changes colour and lands on a fill nobody
 * re-measured it against.
 *
 * `api/features/art_direction/lint.py`'s `lint_art_direction_with_brand` runs
 * the same two pairs at brand-kit save, so a marketer is told at the point of
 * choosing rather than at the point of rendering. This is the render-time half,
 * and it exists because a stored brand kit can predate a change to the art
 * direction it is being applied to. */
function resolveGround(
  raw: Color,
  supplied: string,
  ad: ArtDirection,
): Result<ResolvedPalette> {
  if (!passes(ad.color.ink, raw)) {
    return err(
      'invalid_input',
      `${supplied} is too close in tone to ${ad.id}'s type for text to read on it. ` +
        'This art direction sets near-black type directly on your brand colour at ' +
        'full strength, so it needs a lighter one — or an art direction that uses ' +
        'your colour as an accent instead of as the page.',
    );
  }
  if (!passes(raw, ad.color.accent)) {
    return err(
      'invalid_input',
      `${supplied} cannot be read on ${ad.id}'s button fill. This art direction ` +
        'sets the page colour as the label on its buttons, and those two are too ' +
        'close together to tell apart.',
    );
  }
  return ok({ accent: null, accentRaw: raw, ground: raw });
}
