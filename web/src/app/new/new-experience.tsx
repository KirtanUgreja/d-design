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

import { useState } from 'react';

import { directBrief, OutlineEditor } from '@/features/director';
import { streamBuild, type GenerationEvent } from '@/features/generation';
import { IntakeScreen } from '@/features/intake';
import type { Brief, Outline } from '@/schema';

type Stage =
  | { kind: 'intake' }
  | { kind: 'directing' }
  | { kind: 'outline'; outline: Outline }
  | { kind: 'building'; events: GenerationEvent[] };

export function NewExperience() {
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
    setStage({ kind: 'building', events: [] });
    for await (const event of streamBuild(experienceId, { brief, outline: approved })) {
      setStage((prev) =>
        prev.kind === 'building' ? { ...prev, events: [...prev.events, event] } : prev,
      );
    }
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
        <pre className="px-6 py-16 text-xs text-neutral-400">
          {JSON.stringify(stage.events, null, 2)}
        </pre>
      )}
    </main>
  );
}
