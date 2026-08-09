'use client';

// The interactive shell around the pure renderer — selection, toggles, and
// the RTL/motion controls all live here, never inside src/features/renderer/
// (patterns.md rule 2: modes wrap the core, they don't get passed into it).
// The motion toggle itself is the real one from features/present, not a
// second copy — this page is a preview of what a published experience does.

import { useState } from 'react';

import type { MotionVocabulary, ResolvedRecord } from '@/features/art-direction';
import { MotionToggle, useMotionPreference } from '@/features/present';
import { SceneRenderer } from '@/features/renderer';
import type { Experience } from '@/schema';

type FixtureName = 'minimal' | 'full' | 'hostile';

export function PrimitivesHarness({
  experiences,
  artDirections,
  motionVocabularies,
}: {
  experiences: Record<FixtureName, Experience>;
  /** Resolved on the server and handed down. This is a client component and
   * art directions are rows since v2 phase 01, so there is nothing here to
   * resolve them with — which is the boundary working, not a limitation. */
  artDirections: ResolvedRecord[];
  /** The other axis, and the reason this harness has two selectors instead of
   * one. Every combination is reachable here — which is the claim phase 02
   * makes, made checkable by eye. */
  motionVocabularies: {
    id: string;
    full: MotionVocabulary;
    reduced: MotionVocabulary;
  }[];
}) {
  // The art-direction switch, and the reason this harness exists at all now:
  // the same fixture, the same eleven primitives, one string apart. If the two
  // do not look like different products here, art direction #2 failed and no
  // amount of token authoring fixes it (docs/v1/spec.md, Risk 4).
  const [adId, setAdId] = useState<string>(artDirections[0]?.artDirection.id ?? '');
  const selected = artDirections.find((r) => r.artDirection.id === adId);
  if (selected === undefined) throw new Error(`primitives: no art direction ${adId}`);
  const { artDirection } = selected;

  // Chosen independently of the art direction, which is the whole of phase 02.
  // Seeded from the *first* direction's `defaultMotion`, so the harness opens on
  // a pairing someone would actually be given — and then never reset when the
  // direction changes, because that is precisely the coupling this phase
  // removed. Switching to editorial-light while cinematic-slow is selected is
  // one of the twelve combinations, not a state to correct.
  const [motionId, setMotionId] = useState<string>(
    artDirections[0]?.record.extensions.defaultMotion ?? '',
  );
  const motion = motionVocabularies.find((m) => m.id === motionId);
  if (motion === undefined) throw new Error(`primitives: no motion ${motionId}`);
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
        {artDirections.map(({ artDirection: ad }) => (
          <button key={ad.id} onClick={() => setAdId(ad.id)} disabled={adId === ad.id}>
            {ad.id}
          </button>
        ))}
        {motionVocabularies.map((m) => (
          <button
            key={m.id}
            onClick={() => setMotionId(m.id)}
            disabled={motionId === m.id}
          >
            {m.id}
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
