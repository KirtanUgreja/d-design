/**
 * renderDeckToHtml — the single-file exporter (phase 05).
 *
 * Takes a built deck + its image assets, server-renders the pure renderer to
 * static markup, and wraps it in the self-contained HTML document: the design
 * family's CSS inlined, a tiny nav shell (arrow keys, Space, buttons, counter,
 * swipe), and `connect-src 'none'` — the file talks to nothing.
 *
 * The deck is readable and complete without JS (progressive enhancement is
 * the floor, frontend.md): the slides are in the markup; the nav shell is the
 * enhancement. Fonts are system-stack in v1; Fontsource data-URI embedding is
 * a phase-05 follow-up that keeps the offline guarantee (the family's faces
 * are already open-license).
 */

import type { Deck } from '@web/schema/generated/Deck.js';
import { familyTokens } from '@web/features/design-system/index.js';
import { renderToStaticMarkup } from 'react-dom/server';

import { DeckRenderer } from '@web/features/renderer/index.js';

export type ExportInput = {
  deck: Deck;
  images?: Record<string, string>;
};

const NAV_SHELL_JS = `
(function () {
  var slides = Array.prototype.slice.call(document.querySelectorAll('.dds-slide'));
  var current = 0;
  var counter = document.getElementById('dds-counter');
  var prevBtn = document.getElementById('dds-prev');
  var nextBtn = document.getElementById('dds-next');

  function show(i) {
    current = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach(function (s, idx) {
      s.style.display = idx === current ? '' : 'none';
    });
    if (counter) counter.textContent = (current + 1) + ' / ' + slides.length;
  }

  function next() { show(current + 1); }
  function prev() { show(current - 1); }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') { e.preventDefault(); next(); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); prev(); }
    else if (e.key === 'Home') { e.preventDefault(); show(0); }
    else if (e.key === 'End') { e.preventDefault(); show(slides.length - 1); }
  });

  var touchX = null;
  document.addEventListener('touchstart', function (e) { touchX = e.touches[0].clientX; });
  document.addEventListener('touchend', function (e) {
    if (touchX === null) return;
    var dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) { dx < 0 ? next() : prev(); }
    touchX = null;
  });

  if (prevBtn) prevBtn.addEventListener('click', prev);
  if (nextBtn) nextBtn.addEventListener('click', next);

  show(0);
})();
`;

export function renderDeckToHtml({ deck, images }: ExportInput): string {
  const spec = familyTokens(deck.family_id);
  if (!spec) {
    throw new Error(`unknown design family: ${deck.family_id}`);
  }

  const cssVars = Object.entries(spec.tokens.css)
    .map(([k, v]) => `${k}: ${v};`)
    .join('\n');

  const body = renderToStaticMarkup(
    <DeckRenderer deck={deck} motion={spec.motion} images={images} />,
  );

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(deck.slides[0]?.title ?? 'Deck')}</title>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'unsafe-inline'; connect-src 'none';">
<style>
:root {
${cssVars}
}
${cssText}
</style>
</head>
<body>
<div class="dds-present">
${body}
</div>
<div class="dds-nav" aria-label="Slide navigation">
  <button id="dds-prev" aria-label="Previous slide">Prev</button>
  <span id="dds-counter">1 / ${deck.slides.length}</span>
  <button id="dds-next" aria-label="Next slide">Next</button>
</div>
<script>${NAV_SHELL_JS}</script>
</body>
</html>
`;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// The renderer stylesheet, inlined as a string at build time (esbuild
// loader: css -> text). The exporter runs in Node and bundles web/src, so the
// CSS is part of the bundle — the single-file guarantee holds.
import cssText from '@web/features/renderer/renderer.css';
