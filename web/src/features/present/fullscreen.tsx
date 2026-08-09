'use client';

// Fullscreen API + a keydown handler, wrapping SceneRenderer — about fifty
// lines, and it's what keeps the word "presentation" honest
// (docs/v1/spec.md, Risk 3). Interaction lives here, in the wrapper;
// rendering lives in the core; they do not mix (patterns.md rule 2).

import { useCallback, useEffect, useRef, useState } from 'react';

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import { SceneRenderer } from '@/features/renderer';
import type { Scene } from '@/schema';

import { MotionToggle, useMotionPreference } from './motion-toggle';

const CONTROL_STYLE = {
  background: 'rgba(0, 0, 0, 0.6)',
  color: '#f4f4f5',
  border: '1px solid rgba(255, 255, 255, 0.2)',
  borderRadius: '0.375rem',
  padding: '0.375rem 0.75rem',
  fontSize: '0.8125rem',
  fontFamily: 'system-ui, sans-serif',
} as const;

export function PresentedExperience({
  scenes,
  artDirection,
  motion,
}: {
  scenes: Scene[];
  artDirection: ArtDirection;
  /** The art direction's own full-motion vocabulary. The reduced-motion swap
   * happens below, in this wrapper, because it is the only layer allowed to
   * read the environment (patterns.md rule 6). */
  motion: MotionVocabulary;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [index, setIndex] = useState(0);
  const { vocabulary, reduced, toggle } = useMotionPreference(motion);

  useEffect(() => {
    const onChange = () =>
      setIsFullscreen(document.fullscreenElement === containerRef.current);
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  const goTo = useCallback(
    (next: number) => {
      const clamped = Math.min(Math.max(next, 0), scenes.length - 1);
      setIndex(clamped);
      const scene = scenes[clamped];
      if (scene) {
        document
          .getElementById(`scene-${scene.id}`)
          ?.scrollIntoView({ behavior: 'smooth' });
      }
    },
    [scenes],
  );

  useEffect(() => {
    if (!isFullscreen) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') goTo(index + 1);
      else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') goTo(index - 1);
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [isFullscreen, index, goTo]);

  const enterFullscreen = useCallback(() => {
    containerRef.current?.requestFullscreen().catch(() => {});
  }, []);
  const exitFullscreen = useCallback(() => {
    if (document.fullscreenElement) void document.exitFullscreen();
  }, []);

  return (
    <div
      ref={containerRef}
      // Fullscreen makes this element the whole screen, and the UA gives it
      // `overflow: visible` — so the scenes below the first overflow a box
      // nothing can scroll. The document behind it cannot scroll either,
      // because the fullscreen element is painted over it. The result was a
      // presentation mode that showed scene one and had no way to reach scene
      // two: arrow keys fired, `scrollIntoView` ran, and nothing moved.
      //
      // Found in the v1 acceptance run — "Fullscreen, navigate with arrow keys"
      // is the checkbox, and Risk 3 in docs/v1/spec.md is why it is on the
      // list: fullscreen plus keyboard nav is the minimum that keeps the word
      // "presentation" honest. It had never been exercised end to end; the
      // fullscreen call and the keydown handler were each fine on their own.
      //
      // A conditional inline style rather than a stylesheet rule on
      // `:fullscreen`, because this is the interaction wrapper — modes live
      // out here, and the renderer core stays pure (patterns.md rule 2).
      style={isFullscreen ? { blockSize: '100%', overflowY: 'auto' } : undefined}
    >
      <div
        style={{
          position: 'fixed',
          insetBlockStart: 0,
          insetInlineEnd: 0,
          zIndex: 100,
          display: 'flex',
          gap: '0.5rem',
          padding: '0.75rem 1rem',
        }}
      >
        {/* A fixed dark pill regardless of the scene behind it — the
            control bar has to read on every art direction and every scene,
            not just the ones with a dark bg. */}
        <button
          type="button"
          onClick={isFullscreen ? exitFullscreen : enterFullscreen}
          style={CONTROL_STYLE}
        >
          {isFullscreen ? 'Exit' : 'Present'}
        </button>
        <MotionToggle reduced={reduced} onToggle={toggle} style={CONTROL_STYLE} />
      </div>
      <SceneRenderer scenes={scenes} artDirection={artDirection} motion={vocabulary} />
    </div>
  );
}
