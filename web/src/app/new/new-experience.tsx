'use client';

// The product path, end to end: Intake -> the outline gate -> Build
// (docs/v1/spec.md -> Verification). This is app-level composition — three
// features wired together — which is why it lives in the route tree rather
// than inside any one of them.
//
// It overlaps with `app/dev/director/director-harness.tsx` by about twenty
// lines of glue, and that harness is deliberately left alone: it is phase 07's
// standing judgment surface for the Director *in isolation*, hardcoded brief
// and all, which is exactly what you want when the thing under test is the
// Director rather than the flow. The two are expected to diverge rather than
// converge — this route is where the generation watch's real motion design
// lands (docs/design/app.md -> "3. The generation watch"), and that is design
// the harness must not have if it is to stay a plain readout.
//
// Deferred here, named rather than forgotten: the generation watch is still a
// list of events, and the outline gate is still `OutlineEditor`'s plain
// markup. Both are phase-06/07 deferrals already recorded in those phases.

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { loadBrand } from '@/features/brand';
import { directBrief, OutlineEditor } from '@/features/director';
import {
  saveBuiltExperience,
  streamBuild,
  type GenerationEvent,
} from '@/features/generation';
import { IntakeScreen } from '@/features/intake';
import type { Brief, Outline, Scene } from '@/schema';

type Stage =
  | { kind: 'intake' }
  | { kind: 'directing' }
  | { kind: 'outline'; outline: Outline }
  | { kind: 'building'; events: GenerationEvent[]; saving: boolean };

/** What to call a scene in the watch list. Its headline if it has one — the
 * copy is the only part a person recognises — and its narrative intent
 * otherwise, for the scenes that are a photograph or a Slot and have no
 * words at all. */
function sceneLabel(scene: Scene): string {
  for (const block of scene.blocks) {
    if (block.props.type === 'headline') return block.props.text;
  }
  return scene.intent;
}

export function NewExperience() {
  const router = useRouter();
  const [experienceId] = useState(() => crypto.randomUUID());
  // Held above the stage: the Brief outlives Intake. Build needs it, and the
  // approved-claims record is not something the user passes through and leaves
  // behind (docs/v1/plan/08-intake.md).
  const [brief, setBrief] = useState<Brief | null>(null);
  const [stage, setStage] = useState<Stage>({ kind: 'intake' });
  const [error, setError] = useState<string | null>(null);

  async function runDirector(approved: Brief) {
    setStage({ kind: 'directing' });
    setError(null);
    const result = await directBrief(experienceId, approved);
    if (!result.ok) {
      setError(`${result.error.code}: ${result.error.message}`);
      setStage({ kind: 'intake' });
      return;
    }
    setStage({ kind: 'outline', outline: result.value });
  }

  async function runBuild(approved: Outline) {
    if (!brief) return;
    setStage({ kind: 'building', events: [], saving: false });
    setError(null);

    // Collected here rather than derived from `events` at the end: the stage's
    // event list is what the watch renders, and reading a render list back as
    // a data structure is how the two quietly diverge.
    const scenes: Scene[] = [];
    for await (const event of streamBuild(experienceId, { brief, outline: approved })) {
      if (event.type === 'scene') scenes.push(event.scene);
      setStage((prev) =>
        prev.kind === 'building' ? { ...prev, events: [...prev.events, event] } : prev,
      );
    }
    await save(approved.title, scenes);
  }

  // The step that turns a finished stream into something with a URL. Until the
  // acceptance pass this did not exist and the scenes were simply dropped on
  // the floor when the page unmounted (docs/v1/plan/README.md -> "v1 is done
  // when": every checkbox after "Build streams 8 scenes" depends on this).
  async function save(title: string, scenes: Scene[]) {
    setStage((prev) => (prev.kind === 'building' ? { ...prev, saving: true } : prev));

    // A brand kit is legitimately absent for a new user — it is asked for
    // second, after the first artifact exists (docs/v1/plan/10-brand-and-uploads.md).
    // `brandId` is opaque text on the row, so "default" is a real value and not
    // a placeholder that breaks a join.
    const brand = await loadBrand();
    const brandId = brand.ok ? brand.value.id : 'default';

    const saved = await saveBuiltExperience(experienceId, { title, scenes, brandId });
    if (!saved.ok) {
      setStage((prev) => (prev.kind === 'building' ? { ...prev, saving: false } : prev));
      setError(`${saved.error.code}: ${saved.error.message}`);
      return;
    }
    router.push(`/edit/${saved.value.id}`);
  }

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100">
      {stage.kind === 'intake' && (
        <>
          <IntakeScreen experienceId={experienceId} onBrief={setBrief} />
          <div className="mx-auto max-w-2xl px-6 pb-16">
            {error && (
              <p role="alert" className="mb-3 text-sm text-red-400">
                {error}
              </p>
            )}
            {/* Only reachable once a Brief exists, so it is rendered then
                rather than disabled until then. */}
            {brief && (
              <button
                type="button"
                className="rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 hover:bg-white"
                onClick={() => void runDirector(brief)}
              >
                Generate outline
              </button>
            )}
          </div>
        </>
      )}

      {stage.kind === 'directing' && (
        <p className="px-6 py-16 text-sm text-neutral-400">Planning the narrative…</p>
      )}

      {stage.kind === 'outline' && (
        <div className="mx-auto max-w-2xl px-6 py-16">
          <OutlineEditor
            initial={stage.outline}
            onApprove={(outline) => void runBuild(outline)}
            onRegenerate={() => {
              if (brief) void runDirector(brief);
            }}
            regenerating={false}
          />
        </div>
      )}

      {stage.kind === 'building' && (
        <div className="mx-auto max-w-2xl px-6 py-16">
          <h2 className="text-sm font-medium text-neutral-300">
            {stage.saving ? 'Saving…' : 'Building the experience…'}
          </h2>
          {/* Still not the generation watch the design doc asks for — that is
              phase 06's recorded deferral and it is a motion-design job, not a
              markup one. This is the honest interim: one line per scene as it
              lands, in the order the outline promised, so the forty seconds
              read as progress rather than as a stalled page. The raw event
              dump this replaced was neither. */}
          <ol className="mt-4 space-y-2">
            {stage.events.map((event, i) => (
              <li key={i} className="text-sm">
                {event.type === 'scene' && (
                  <span className="text-neutral-200">
                    <span className="text-neutral-500">{event.index + 1}.</span>{' '}
                    {sceneLabel(event.scene)}
                  </span>
                )}
                {event.type === 'repair' && (
                  <span className="text-neutral-500">
                    scene {event.index + 1} needed a second pass
                  </span>
                )}
                {event.type === 'error' && (
                  <span className="text-red-400">
                    scene {event.index + 1} could not be built ({event.code})
                  </span>
                )}
                {event.type === 'done' && (
                  <span className="text-neutral-400">{event.count} scenes built</span>
                )}
              </li>
            ))}
          </ol>
          {error && (
            <p role="alert" className="mt-6 text-sm text-red-400">
              {error}
            </p>
          )}
        </div>
      )}
    </main>
  );
}
