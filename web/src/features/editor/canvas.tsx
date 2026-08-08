'use client';

// Selection lives outside the renderer (docs/coderules/patterns.md rule 2).
// This file imports `@/features/renderer`'s index and nothing deeper: if a
// selection overlay ever needed to reach into `renderer/blocks/`, the design
// would be wrong. Nothing about selection enters `SceneRenderer`, which still
// takes exactly `(scenes, artDirection, motion)` and has no idea it is being
// edited.
//
// The guarantee that buys: what you edit is byte-for-byte what you publish.
//
// True scale, always — fit-width and 100%, nothing else. Any zoom weakens the
// guarantee the whole product rests on, which is also why selection is a
// hairline and a label rather than a saturated box painted over a designed
// page.

import { useCallback, useEffect, useRef, useState } from 'react';

import { SceneRenderer } from '@/features/renderer';
import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import type { Scene } from '@/schema';

import type { Selection } from './store';

interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}

export function Canvas({
  scenes,
  artDirection,
  motion,
  selection,
  onSelect,
  children,
}: {
  scenes: Scene[];
  artDirection: ArtDirection;
  motion: MotionVocabulary;
  selection: Selection | null;
  onSelect: (selection: Selection | null) => void;
  /** The element-scoped prompt, rendered under the selection box by the
   * caller. It appears only with a selection, because an always-present
   * prompt invites page-level requests the patch shape cannot serve. */
  children?: React.ReactNode;
}) {
  const host = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState<Box | null>(null);

  const measure = useCallback(() => {
    if (!host.current || !selection) return setBox(null);
    const target = host.current.querySelector(`[data-block-id="${selection.blockId}"]`);
    if (!(target instanceof HTMLElement)) return setBox(null);
    const outer = host.current.getBoundingClientRect();
    const inner = target.getBoundingClientRect();
    setBox({
      top: inner.top - outer.top,
      left: inner.left - outer.left,
      width: inner.width,
      height: inner.height,
    });
  }, [selection]);

  useEffect(() => {
    measure();
    // The page moves under the selection for reasons the editor does not
    // control — a reveal finishing, an image loading, a patch reflowing the
    // block being edited. Observing the host covers all of them without a
    // per-cause listener.
    const observer = new ResizeObserver(measure);
    if (host.current) observer.observe(host.current);
    window.addEventListener('scroll', measure, true);
    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', measure, true);
    };
  }, [measure]);

  function pick(event: React.MouseEvent) {
    const el =
      event.target instanceof Element ? event.target.closest('[data-block-id]') : null;
    const blockId = el instanceof HTMLElement ? el.dataset['blockId'] : undefined;
    if (!blockId) return onSelect(null);
    const scene = scenes.find((s) => s.blocks.some((b) => b.id === blockId));
    onSelect(scene ? { sceneId: scene.id, blockId } : null);
  }

  return (
    <div ref={host} className="relative flex-1 overflow-auto">
      {/* The click handler sits on a wrapper, not inside the renderer. A
          published page has no such wrapper and is byte-identical without it. */}
      <div onClick={pick}>
        <SceneRenderer scenes={scenes} artDirection={artDirection} motion={motion} />
      </div>

      {box && (
        <>
          <div
            aria-hidden
            className="pointer-events-none absolute z-10 outline-1 outline-sky-400"
            style={{
              top: box.top,
              left: box.left,
              width: box.width,
              height: box.height,
            }}
          />
          <div
            className="absolute z-10"
            style={{ top: box.top + box.height, left: box.left, width: box.width }}
          >
            {children}
          </div>
        </>
      )}
    </div>
  );
}
