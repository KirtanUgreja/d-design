'use client';

// The outline gate (docs/v1/plan/07-director.md -> "The gate is the
// product decision"): Build cannot run until the user approves. Plain
// markup, functional over designed — the scene-card visual treatment,
// motion, claim-provenance highlighting, and "time as a range" copy the
// doc asks for are named, deliberate deferrals, not oversights. What is
// NOT deferred: every edit refuses to produce an invalid outline
// (`outline.ts`), and Approve is the only path to Build — this component
// never calls Build itself, it only ever hands the approved Outline to
// its caller.

import { useState } from 'react';

import type { Outline } from '@/schema';

import {
  addScene,
  changeLayoutHint,
  changeSceneIntent,
  deleteScene,
  moveScene,
  retitleOutline,
  LAYOUT_HINTS,
  SCENE_INTENTS,
  type LayoutHint,
  type SceneIntent,
} from './outline';

export function OutlineEditor({
  initial,
  onApprove,
  onRegenerate,
  regenerating,
}: {
  initial: Outline;
  onApprove: (outline: Outline) => void;
  onRegenerate: () => void;
  regenerating: boolean;
}) {
  const [outline, setOutline] = useState(initial);
  const [error, setError] = useState<string | null>(null);

  function apply(result: ReturnType<typeof moveScene>) {
    if (result.ok) {
      setOutline(result.value);
      setError(null);
    } else {
      setError(result.error.message);
    }
  }

  return (
    <div>
      <input
        value={outline.title}
        onChange={(e) => apply(retitleOutline(outline, e.target.value))}
        aria-label="Outline title"
      />

      {error && <p role="alert">{error}</p>}

      <ol>
        {outline.scenes.map((scene, index) => (
          <li key={index}>
            <select
              value={scene.intent}
              onChange={(e) =>
                apply(changeSceneIntent(outline, index, e.target.value as SceneIntent))
              }
              aria-label={`Scene ${index + 1} intent`}
            >
              {SCENE_INTENTS.map((intent) => (
                <option key={intent} value={intent}>
                  {intent}
                </option>
              ))}
            </select>

            <span>{scene.beat}</span>

            <select
              value={scene.layoutHint ?? ''}
              onChange={(e) =>
                apply(
                  changeLayoutHint(
                    outline,
                    index,
                    (e.target.value || null) as LayoutHint | null,
                  ),
                )
              }
              aria-label={`Scene ${index + 1} layout`}
            >
              <option value="">(none)</option>
              {LAYOUT_HINTS.map((layout) => (
                <option key={layout} value={layout}>
                  {layout}
                </option>
              ))}
            </select>

            <button type="button" onClick={() => apply(moveScene(outline, index, 'up'))}>
              move up
            </button>
            <button
              type="button"
              onClick={() => apply(moveScene(outline, index, 'down'))}
            >
              move down
            </button>
            <button type="button" onClick={() => apply(deleteScene(outline, index))}>
              delete
            </button>
            <button
              type="button"
              onClick={() =>
                apply(
                  addScene(outline, index, {
                    intent: 'problem',
                    beat: 'new scene',
                    layoutHint: null,
                  }),
                )
              }
            >
              add scene after
            </button>
          </li>
        ))}
      </ol>

      <button type="button" onClick={onRegenerate} disabled={regenerating}>
        {regenerating ? 'Regenerating…' : 'Regenerate'}
      </button>
      <button type="button" onClick={() => onApprove(outline)}>
        Approve
      </button>
    </div>
  );
}
