'use client';

// The in-page reduced-motion control ships in the runtime, not the art
// direction — every published experience gets it for free rather than each
// art direction re-implementing it (docs/v1/plan/05-publish-present-embed.md).
// Seeded from the OS setting, overridable for the session — the same
// pattern app/dev/primitives used in phase 04, promoted here so the real
// published page and the dev review harness share one implementation.

import type { CSSProperties } from 'react';
import { useState, useSyncExternalStore } from 'react';

import type { MotionVocabulary } from '@/features/art-direction';

function subscribeToReducedMotionPreference(onChange: () => void): () => void {
  const query = matchMedia('(prefers-reduced-motion: reduce)');
  query.addEventListener('change', onChange);
  return () => query.removeEventListener('change', onChange);
}

function useSystemPrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeToReducedMotionPreference,
    () => matchMedia('(prefers-reduced-motion: reduce)').matches,
    () => false,
  );
}

/** Both vocabularies are passed in; this hook only decides *which*.
 *
 * `full` used to be `CINEMATIC_MOTION` by name, which was invisible while there
 * was one art direction and wrong the moment there were two. The reduced half
 * used to be a global constant, which was right while collapsing to opacity was
 * the whole of what reduced motion meant — and became too coarse in v2 phase
 * 02, when each vocabulary started declaring its own: 200ms under
 * `mechanical-snap` and 200ms under `physics-playful` are not the same design
 * even when both are a bare fade.
 *
 * What has not changed is that reduced motion is still a *floor* rather than a
 * design choice. A vocabulary declares its duration and nothing else;
 * `fromMotionRecord` builds the rest, so there is no shape in which one could
 * declare a reduced mode that moves.
 *
 * This is the one place in the motion path that reads the environment, and it
 * is a wrapper — the renderer core may not (rule 6), which is why it takes a
 * vocabulary rather than deriving one. */
export function useMotionPreference(vocabularies: {
  full: MotionVocabulary;
  reduced: MotionVocabulary;
}): {
  vocabulary: MotionVocabulary;
  reduced: boolean;
  toggle: () => void;
} {
  const systemReduced = useSystemPrefersReducedMotion();
  const [override, setOverride] = useState<boolean | null>(null);
  const reduced = override ?? systemReduced;
  return {
    vocabulary: reduced ? vocabularies.reduced : vocabularies.full,
    reduced,
    toggle: () => setOverride(!reduced),
  };
}

export function MotionToggle({
  reduced,
  onToggle,
  style,
}: {
  reduced: boolean;
  onToggle: () => void;
  style?: CSSProperties;
}) {
  return (
    <button type="button" onClick={onToggle} style={style}>
      motion: {reduced ? 'reduced' : 'full'}
    </button>
  );
}
