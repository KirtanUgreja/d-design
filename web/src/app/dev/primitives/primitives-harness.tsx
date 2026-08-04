'use client';

// The interactive shell around the pure renderer — selection, toggles, and
// the RTL/motion controls all live here, never inside src/features/renderer/
// (patterns.md rule 2: modes wrap the core, they don't get passed into it).

import { useState, useSyncExternalStore } from 'react';

import {
  CINEMATIC_DARK,
  CINEMATIC_MOTION,
  REDUCED_MOTION,
} from '@/features/art-direction';
import { SceneRenderer } from '@/features/renderer';
import type { Experience } from '@/schema';

type FixtureName = 'minimal' | 'full' | 'hostile';

function subscribeToReducedMotionPreference(onChange: () => void): () => void {
  const query = matchMedia('(prefers-reduced-motion: reduce)');
  query.addEventListener('change', onChange);
  return () => query.removeEventListener('change', onChange);
}

/** Seeds the toggle from the OS setting on first paint; the button below can
 * still override it for the session. Never read inside the renderer itself —
 * this is the wrapper the purity rule expects to do exactly this. */
function useSystemPrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeToReducedMotionPreference,
    () => matchMedia('(prefers-reduced-motion: reduce)').matches,
    () => false,
  );
}

export function PrimitivesHarness({
  experiences,
}: {
  experiences: Record<FixtureName, Experience>;
}) {
  const systemReduced = useSystemPrefersReducedMotion();
  const [reducedOverride, setReducedOverride] = useState<boolean | null>(null);
  const [dir, setDir] = useState<'ltr' | 'rtl'>('ltr');
  const [fixture, setFixture] = useState<FixtureName>('full');

  const reduced = reducedOverride ?? systemReduced;
  const experience = experiences[fixture];

  return (
    <div>
      <div
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          display: 'flex',
          gap: '0.75rem',
          padding: '0.75rem 1rem',
          background: '#111',
          color: '#eee',
          fontFamily: 'system-ui, sans-serif',
          fontSize: '0.875rem',
        }}
      >
        {(['minimal', 'full', 'hostile'] as const).map((name) => (
          <button key={name} onClick={() => setFixture(name)} disabled={fixture === name}>
            {name}
          </button>
        ))}
        <span style={{ marginInlineStart: 'auto' }} />
        <button onClick={() => setDir(dir === 'ltr' ? 'rtl' : 'ltr')}>dir: {dir}</button>
        <button onClick={() => setReducedOverride(!reduced)}>
          motion: {reduced ? 'reduced' : 'full'}
        </button>
      </div>
      <div dir={dir}>
        <SceneRenderer
          scenes={experience.scenes}
          artDirection={CINEMATIC_DARK}
          motion={reduced ? REDUCED_MOTION : CINEMATIC_MOTION}
        />
      </div>
    </div>
  );
}
