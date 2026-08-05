'use client';

// The interactive shell around the pure renderer — selection, toggles, and
// the RTL/motion controls all live here, never inside src/features/renderer/
// (patterns.md rule 2: modes wrap the core, they don't get passed into it).
// The motion toggle itself is the real one from features/present, not a
// second copy — this page is a preview of what a published experience does.

import { useState } from 'react';

import { CINEMATIC_DARK } from '@/features/art-direction';
import { MotionToggle, useMotionPreference } from '@/features/present';
import { SceneRenderer } from '@/features/renderer';
import type { Experience } from '@/schema';

type FixtureName = 'minimal' | 'full' | 'hostile';

export function PrimitivesHarness({
  experiences,
}: {
  experiences: Record<FixtureName, Experience>;
}) {
  const { vocabulary, reduced, toggle } = useMotionPreference();
  const [dir, setDir] = useState<'ltr' | 'rtl'>('ltr');
  const [fixture, setFixture] = useState<FixtureName>('full');

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
        <MotionToggle reduced={reduced} onToggle={toggle} />
      </div>
      <div dir={dir}>
        <SceneRenderer
          scenes={experience.scenes}
          artDirection={CINEMATIC_DARK}
          motion={vocabulary}
        />
      </div>
    </div>
  );
}
