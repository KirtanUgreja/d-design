'use client';

// App-level composition: the canvas, the panel and the element prompt wired to
// one store (docs/v1/plan/09-editor.md). Three features meeting, so it lives in
// the route tree rather than inside any of them.

import { useCallback, useRef, useState } from 'react';

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import {
  Canvas,
  ElementPrompt,
  PropertyPanel,
  editBlock,
  selectedBlock,
  useEditor,
} from '@/features/editor';
import type { EditResult, Scene } from '@/schema';

import { publishEdited, unpublishEdited } from './actions';
import { PublishBar } from './publish-bar';

export function EditorScreen({
  experienceId,
  title,
  artDirection,
  motion,
  initialScenes,
  stored,
}: {
  experienceId: string;
  title: string;
  /** The experience's own art direction, already resolved. What-you-edit-is-
   * what-you-ship means the canvas renders the direction the artifact will
   * publish under, not the one this component happens to import — and since
   * v2 phase 01 that direction is a database row, so it is resolved on the
   * server and handed down rather than looked up here. */
  artDirection: ArtDirection;
  motion: MotionVocabulary;
  initialScenes: Scene[];
  /** False when this is the phase 01 fixture rather than a stored experience —
   * see the route. Publishing something `api` has never heard of cannot work,
   * and the bar says so up front rather than at the click. */
  stored: boolean;
}) {
  // `useState`'s initializer, not an effect: the store is seeded once, on the
  // first render, and a reset in an effect would fight an in-progress edit on
  // every remount.
  useState(() => useEditor.getState().reset(initialScenes));

  const scenes = useEditor((s) => s.scenes);
  const selection = useEditor((s) => s.selection);
  const error = useEditor((s) => s.error);
  const select = useEditor((s) => s.select);
  const patch = useEditor((s) => s.patch);
  const undo = useEditor((s) => s.undo);
  const redo = useEditor((s) => s.redo);
  const block = useEditor(selectedBlock);

  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<EditResult | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [stylingReaches, setStylingReaches] = useState(0);
  const inFlight = useRef<AbortController | null>(null);

  const runEdit = useCallback(
    async (instruction: string) => {
      const state = useEditor.getState();
      const current = state.selection;
      const scene = state.scenes.find((s) => s.id === current?.sceneId);
      if (!current || !scene) return;

      // One request at a time per selection: a superseded edit's response is
      // an edit the user has already moved past.
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;

      setPending(true);
      setEditError(null);
      const response = await editBlock(
        experienceId,
        { scene, blockId: current.blockId, instruction },
        controller.signal,
      );
      setPending(false);
      if (!response.ok) {
        setEditError(response.error.message);
        return;
      }
      setResult(response.value);

      // The AI's half becomes the identical patch the panel produces, applied
      // through the identical code path — one shape, two producers, one
      // validation site, and therefore one undo stack.
      const props = response.value.props;
      if (props && Object.keys(props).length > 0) {
        patch({ sceneId: current.sceneId, blockId: current.blockId, props });
      }
    },
    [experienceId, patch],
  );

  // Never a model call per keystroke. `ElementPrompt` submits on Enter rather
  // than on change, so this guards the case where it does not — a held key, a
  // paste, a double-submit — at three lines and no dependency.
  //
  // Written out rather than wrapped around `debounce`: a debounced function
  // has to survive re-renders, so it would have to live in a ref, and reading
  // a ref during render is what the react-hooks rules (and the React Compiler
  // behind them) correctly refuse. A timer in a ref, cleared in a callback, is
  // the same three lines in the shape React actually allows.
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const submitEdit = useCallback(
    (instruction: string) => {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => void runEdit(instruction), 250);
    },
    [runEdit],
  );

  const [publishing, setPublishing] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);

  const runPublish = useCallback(async () => {
    setPublishing(true);
    setPublishError(null);
    // The store's scenes, read at click time rather than from the render's
    // closure: the last keystroke before the click has to be in what ships.
    const result = await publishEdited(experienceId, useEditor.getState().scenes);
    setPublishing(false);
    if (!result.ok) {
      setPublishError(result.error.message || result.error.code);
      return;
    }
    setRevealed(true);
  }, [experienceId]);

  const runUnpublish = useCallback(async () => {
    setPublishing(true);
    const result = await unpublishEdited(experienceId);
    setPublishing(false);
    if (!result.ok) {
      setPublishError(result.error.message || result.error.code);
      return;
    }
    setRevealed(false);
  }, [experienceId]);

  return (
    <main
      className="flex h-screen flex-col bg-neutral-950 text-neutral-100"
      onKeyDown={(e) => {
        if (!(e.metaKey || e.ctrlKey) || e.key !== 'z') return;
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      }}
      tabIndex={-1}
    >
      <PublishBar
        id={experienceId}
        title={title}
        publishable={stored}
        published={revealed}
        pending={publishing}
        error={publishError}
        onPublish={() => void runPublish()}
        onUnpublish={() => void runUnpublish()}
        onDismiss={() => setRevealed(false)}
      />

      {/* The row the bar sits above: canvas and panel, filling what is left. */}
      <div className="flex min-h-0 flex-1">
        <Canvas
          scenes={scenes}
          artDirection={artDirection}
          motion={motion}
          selection={selection}
          onSelect={(next) => {
            select(next);
            setResult(null);
            setEditError(null);
          }}
        >
          <ElementPrompt
            onSubmit={submitEdit}
            pending={pending}
            result={result}
            error={editError}
          />
        </Canvas>

        {block && selection ? (
          <PropertyPanel
            block={block}
            sceneId={selection.sceneId}
            onPatch={patch}
            onReachForStyling={() => setStylingReaches((n) => n + 1)}
            error={error}
          />
        ) : (
          <aside className="w-72 shrink-0 border-l border-neutral-800 p-4 text-xs text-neutral-500">
            Select anything on the page to edit it.
            {/* ponytail: the styling-reach count is state, not an event sink.
              The phase doc wants it counted — "the cheapest high-signal metric
              in the product" — and there is no analytics transport in v1, so it
              is surfaced here rather than dropped. Upgrade: the v3 beacon. */}
            {stylingReaches > 0 && (
              <span className="mt-2 block">
                styling-control reaches this session: {stylingReaches}
              </span>
            )}
          </aside>
        )}
      </div>
    </main>
  );
}
