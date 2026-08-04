import type { ArtDirection } from '@/features/art-direction';
import { toCssVars } from '@/features/art-direction';

import type { SlotProps } from './block-props';

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
        blockSize: props.height === 'viewport' ? '100vh' : '400px',
        border: 'none',
      }}
    />
  );
}
