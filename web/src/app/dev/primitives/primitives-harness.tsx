'use client';

// The interactive shell around the pure renderer — selection, toggles, and
// the RTL/motion controls all live here, never inside src/features/renderer/
// (patterns.md rule 2: modes wrap the core, they don't get passed into it).
// The motion toggle itself is the real one from features/present, not a
// second copy — this page is a preview of what a published experience does.

import { useState } from 'react';

import {
  ART_DIRECTION_IDS,
  resolveArtDirection,
  type ArtDirectionId,
} from '@/features/art-direction';
import { MotionToggle, useMotionPreference } from '@/features/present';
import { SceneRenderer } from '@/features/renderer';
import type { Experience } from '@/schema';

type FixtureName = 'minimal' | 'full' | 'hostile';

export function PrimitivesHarness({
  experiences,
}: {
  experiences: Record<FixtureName, Experience>;
}) {
  // The art-direction switch, and the reason this harness exists at all now:
  // the same fixture, the same eleven primitives, one string apart. If the two
  // do not look like different products here, art direction #2 failed and no
  // amount of token authoring fixes it (docs/v1/spec.md, Risk 4).
  const [adId, setAdId] = useState<ArtDirectionId>('cinematic-dark');
  const { artDirection, motion } = resolveArtDirection(adId);
  const { vocabulary, reduced, toggle } = useMotionPreference(motion);
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
        {ART_DIRECTION_IDS.map((id) => (
          <button key={id} onClick={() => setAdId(id)} disabled={adId === id}>
            {id}
          </button>
        ))}
        <button onClick={() => setDir(dir === 'ltr' ? 'rtl' : 'ltr')}>dir: {dir}</button>
        <MotionToggle reduced={reduced} onToggle={toggle} />
      </div>
      <div dir={dir}>
        <SceneRenderer
          scenes={experience.scenes}
          artDirection={artDirection}
          motion={vocabulary}
        />
      </div>
    </div>
  );
}
