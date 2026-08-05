'use client';

// Fullscreen API + a keydown handler, wrapping SceneRenderer — about fifty
// lines, and it's what keeps the word "presentation" honest
// (docs/v1/spec.md, Risk 3). Interaction lives here, in the wrapper;
// rendering lives in the core; they do not mix (patterns.md rule 2).

import { useCallback, useEffect, useRef, useState } from 'react';

import type { ArtDirection } from '@/features/art-direction';
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
}: {
  scenes: Scene[];
  artDirection: ArtDirection;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [index, setIndex] = useState(0);
  const { vocabulary, reduced, toggle } = useMotionPreference();

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
    <div ref={containerRef}>
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
