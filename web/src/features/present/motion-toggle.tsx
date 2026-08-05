'use client';

// The in-page reduced-motion control ships in the runtime, not the art
// direction — every published experience gets it for free rather than each
// art direction re-implementing it (docs/v1/plan/05-publish-present-embed.md).
// Seeded from the OS setting, overridable for the session — the same
// pattern app/dev/primitives used in phase 04, promoted here so the real
// published page and the dev review harness share one implementation.

import type { CSSProperties } from 'react';
import { useState, useSyncExternalStore } from 'react';

import {
  CINEMATIC_MOTION,
  REDUCED_MOTION,
  type MotionVocabulary,
} from '@/features/art-direction';

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

export function useMotionPreference(): {
  vocabulary: MotionVocabulary;
  reduced: boolean;
  toggle: () => void;
} {
  const systemReduced = useSystemPrefersReducedMotion();
  const [override, setOverride] = useState<boolean | null>(null);
  const reduced = override ?? systemReduced;
  return {
    vocabulary: reduced ? REDUCED_MOTION : CINEMATIC_MOTION,
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
