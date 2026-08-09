// The real typefaces, inlined into the screenshot document.
//
// **This is load-bearing, not polish.** The first working screenshot from this
// service came back set in Times: the art direction asked for Fraunces, the
// headless document had no font loaded, and Chromium fell back silently. The
// page *looked* plausible, which is the dangerous part — phase 00's own human
// check says a screenshot that does not look like the page makes phase 09 "a
// vision model confidently reviewing the wrong image", and phase 13's overflow
// measurement is metrics arithmetic on top of the same frame. Wrong font, wrong
// line count, wrong answer, no error anywhere.
//
// Data URIs rather than `file://` or a network fetch. `setContent` gives the
// page an opaque origin with no base URL, so a relative or `file://` reference
// resolves to nothing; embedding the bytes is the one form that behaves the
// same on a laptop and in the container, with no font-config step to get right.
//
// Only the families the requested art direction actually names, and only the
// weights its type scale uses — `FONT_REGISTRY` carries both, so this walks the
// same declaration the browser path does rather than keeping a second list.

import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

import { FONT_REGISTRY, type ArtDirection } from '@/features/art-direction';

const require = createRequire(import.meta.url);

/** Fontsource's on-disk layout: `<pkg>/files/<id>-latin-<weight>-normal.woff2`.
 * Resolved through `require.resolve` rather than a path guess, so a hoisted or
 * relocated `node_modules` is not a silent fallback to Times again. */
function woff2(familyId: string, weight: number): string | null {
  try {
    const file = require.resolve(
      `@fontsource/${familyId}/files/${familyId}-latin-${String(weight)}-normal.woff2`,
    );
    return readFileSync(file).toString('base64');
  } catch {
    // A missing weight is not fatal — the browser synthesizes from a
    // neighbouring one, which is what it would do on the real page too.
    return null;
  }
}

/** `@font-face` rules for exactly the faces this art direction uses.
 *
 * Throws if a family resolves to nothing at all. A missing weight degrades the
 * way the real page degrades; a missing *family* is the silent-Times failure
 * this module exists to prevent, and a screenshot service that cannot load its
 * fonts should stop rather than emit a confidently wrong picture.
 */
export function fontFaceCss(artDirection: ArtDirection): string {
  const rules: string[] = [];

  for (const familyId of new Set(Object.values(artDirection.fonts))) {
    const entry = FONT_REGISTRY[familyId];
    let loaded = 0;
    for (const weight of entry.weights) {
      const data = woff2(familyId, weight);
      if (data === null) continue;
      loaded += 1;
      rules.push(
        `@font-face{font-family:'${entry.family}';font-style:normal;` +
          `font-weight:${String(weight)};font-display:block;` +
          `src:url(data:font/woff2;base64,${data}) format('woff2');}`,
      );
    }
    if (loaded === 0) {
      throw new Error(
        `render: no woff2 found for '${entry.family}' (@fontsource/${familyId}). ` +
          'A screenshot in a fallback face measures and looks like a different page.',
      );
    }
  }

  return rules.join('');
}
