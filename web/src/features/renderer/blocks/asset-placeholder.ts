// The resolve-failure state, and only that.
//
// This was v1's `ponytail:` — there was no resolver, so a flat plate in the
// art direction's own colours *was* what every `Image` block rendered. v2
// phase 15 built the resolver (`asset-url.ts`), and the note's prediction held
// exactly: nothing about the block components' props changed.
//
// Keeping it is deliberate. A missing or unauthorized asset now renders a flat
// plate in the art direction's own colours rather than a browser's broken-image
// glyph on a customer's launch page — the honest failure rather than the only
// path. `video.tsx` still uses it as a poster, which is the same job.

import type { ArtDirection } from '@/features/art-direction';
import { toCssColor } from '@/features/art-direction';

export function placeholderImageSrc(ad: ArtDirection): string {
  const fill = toCssColor(ad.color.bgElevated);
  const stroke = toCssColor(ad.color.hairline);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3" preserveAspectRatio="none"><rect width="4" height="3" fill="${fill}" stroke="${stroke}" stroke-width="0.02"/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
