// ponytail: v1 has no storage.ts (that arrives in phase 10 — brand kit +
// uploads), so `Image`/`Video` blocks have an `assetId` and nothing that
// resolves it to a URL yet. This renders a deterministic placeholder from
// the art direction's own tokens instead of leaving a broken `<img>` — swap
// this for a real resolver when storage.ts exists; nothing about the block
// components' props needs to change when that happens.

import type { ArtDirection } from '@/features/art-direction';
import { toCssColor } from '@/features/art-direction';

export function placeholderImageSrc(ad: ArtDirection): string {
  const fill = toCssColor(ad.color.bgElevated);
  const stroke = toCssColor(ad.color.hairline);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3" preserveAspectRatio="none"><rect width="4" height="3" fill="${fill}" stroke="${stroke}" stroke-width="0.02"/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
