import type { ArtDirection } from '@/features/art-direction';
import { toCssVars } from '@/features/art-direction';

import type { SlotProps } from './block-props';
import { SCENE_FIT_MIN_BLOCK } from '../tokens';

// security/content-and-web.md -> "The Slot sandbox". `allow-same-origin` must
// never be added: with `allow-scripts` alone the frame has an opaque origin —
// localStorage throws, document.cookie is unavailable, parent.document
// throws, no credentialed request is possible. Also never granted:
// allow-top-navigation, allow-popups, allow-modals, allow-forms,
// allow-downloads.
const SANDBOX = 'allow-scripts';
const SLOT_CSP =
  "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:;";

function buildSrcdoc(props: SlotProps, cssVars: Record<string, string>): string {
  // Tokens go in through the same toCssVars() every other block uses — the
  // one token->string path. `html`/`js` are the author's own code, executed
  // only inside this sandbox; that is the feature, not an oversight.
  const vars = Object.entries(cssVars)
    .map(([k, v]) => `${k}:${v};`)
    .join('');
  return [
    '<!doctype html><html><head><meta charset="utf-8">',
    `<meta http-equiv="Content-Security-Policy" content="${SLOT_CSP}">`,
    `<style>:root{${vars}}${props.css ?? ''}</style>`,
    '</head><body>',
    props.html ?? '',
    `<script>${props.js ?? ''}</script>`,
    '</body></html>',
  ].join('');
}

export function SlotBlock({
  props,
  artDirection,
}: {
  props: SlotProps;
  artDirection: ArtDirection;
}) {
  return (
    <iframe
      srcDoc={buildSrcdoc(props, toCssVars(artDirection))}
      sandbox={SANDBOX}
      referrerPolicy="no-referrer"
      title={props.description}
      style={{
        display: 'block',
        inlineSize: '100%',
        // `SlotProps.height: 'viewport'` is the same word the scene-level fit
        // table uses, so it resolves through the same token rather than a
        // second hardcoded literal in a second unit — two vocabularies for one
        // idea is how they drift. This is a `blockSize` and not a
        // `minBlockSize` on purpose: an iframe has no content to be measured
        // against, so it is given an exact box.
        blockSize: props.height === 'viewport' ? SCENE_FIT_MIN_BLOCK : '400px',
        border: 'none',
      }}
    />
  );
}
