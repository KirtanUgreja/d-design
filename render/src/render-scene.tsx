// Scene tree -> a complete HTML document.
//
// **The renderer is imported, never reimplemented.** `SceneRenderer` is the
// same component `web` ships; this file wraps it in a document and nothing
// else. A second copy of the renderer would be the worst duplication available
// in this codebase — rule 6 requires it to behave identically in three
// processes, and two implementations cannot.
//
// esbuild bundles it from `web/src` at build time, which is a *stronger*
// guarantee than the version pin phase 00 originally specified: a pinned
// package can be stale, whereas two consumers of one source tree cannot
// disagree about what the renderer or the schema is.

import { renderToStaticMarkup } from 'react-dom/server';

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import { toCssVars } from '@/features/art-direction';
import { SceneRenderer } from '@/features/renderer';
import type { Scene } from '@/schema';

import { fontFaceCss } from './fonts';

// A reset, and only a reset. Anything opinionated here would be a second
// stylesheet competing with the art direction — the tokens below are the whole
// visual contract.
const DOCUMENT_STYLE = `
  *, *::before, *::after { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  img { max-inline-size: 100%; }
`;

export function renderDocument(
  scenes: Scene[],
  // Tokens, not an id. This service resolved an id against a code table until
  // v2 phase 01 put art directions in the database — and **it holds no
  // credential**, so it cannot read that database and must never be given a
  // way to. What changed instead is the payload: the caller sends the record,
  // `server.ts` parses it with the same generated validator it parses scenes
  // with, and by the time it reaches here it is as validated as the tree is.
  artDirection: ArtDirection,
  // Both vocabularies, and the choice between them made here rather than by the
  // caller. `reducedMotion` defaults true for a screenshot because a reveal
  // caught mid-flight is a half-faded scene, and a critic reviewing one is
  // reviewing a frame no human will ever see.
  //
  // The reduced half used to be `REDUCED_MOTION`, one global constant. Since v2
  // phase 02 each vocabulary declares its own duration and the floor is built
  // from it, so this service takes the pair rather than importing a fallback —
  // and there is no shape in which the one it is handed could move.
  motion: { full: MotionVocabulary; reduced: MotionVocabulary },
  reducedMotion: boolean,
): string {
  const body = renderToStaticMarkup(
    <SceneRenderer
      scenes={scenes}
      artDirection={artDirection}
      motion={reducedMotion ? motion.reduced : motion.full}
    />,
  );

  // The same `toCssVars` the browser path uses — the one token->string path
  // (rule 13). This service does not get its own.
  const rootVars = Object.entries(toCssVars(artDirection))
    .map(([name, value]) => `${name}: ${value};`)
    .join(' ');

  // Fonts first, and `font-display: block` inside them, so the paint waits for
  // the real face rather than flashing a fallback the screenshot might catch.
  return `<!doctype html><html><head><meta charset="utf-8">
<style>${fontFaceCss(artDirection)}</style>
<style>:root { ${rootVars} } ${DOCUMENT_STYLE}</style>
</head><body>${body}</body></html>`;
}
