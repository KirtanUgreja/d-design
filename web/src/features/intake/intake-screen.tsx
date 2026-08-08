'use client';

// The first screen anyone touches, and one of the four that gets real design
// attention (docs/design/app.md -> "1. Intake").
//
// The four decisions this screen exists to embody, from
// docs/v1/plan/08-intake.md -> "The interview is not a chat":
//
//   1. Prompt box first, then a short structured interview. NOT a chat. There
//      are no bubbles and no transcript, because both promise conversational
//      memory and off-task requests that this pipeline will never do — and a
//      chat log is not a Brief, while a structured interview produces one
//      directly.
//   2. Skipping is always available. The prompt box's submit runs the whole
//      interview in one pass over whatever was typed; the questions that
//      remain are only the ones with no answer, and each carries visible
//      progress.
//   3. The Brief stays visible and editable, permanently — `BriefPanel`, and
//      it never goes away once it exists.
//   4. No upload affordance at all. Import is deferred with the fetch worker,
//      and a disabled button explaining why it is disabled is worse than no
//      button. There is deliberately nothing here to find.
//
// No templates and no starting-point gallery either. The examples below are
// real launch briefs, which is the equivalent affordance that does not argue
// against the product's own positioning (docs/v1/market.md).

import { useState } from 'react';

import type { Brief, Question } from '@/schema';

import { BriefPanel } from './brief-panel';
import { advanceInterview, saveBrief } from './intake';

// Every one is commercial work. Generic examples ("a pitch deck", "a school
// project") recruit the cohort that killed Tome — docs/design/principles.md,
// principle 2.
const EXAMPLES = [
  'a product launch',
  'a pricing change',
  'a funding announcement',
] as const;

type Phase =
  { kind: 'prompt' } | { kind: 'question'; question: Question } | { kind: 'working' };

export function IntakeScreen({
  experienceId,
  onBrief,
}: {
  experienceId: string;
  /** Called whenever a Brief exists or changes, so the surrounding flow can
   * enable the outline gate. This screen never calls the Director itself —
   * the same separation `OutlineEditor` keeps from Build. */
  onBrief: (brief: Brief) => void;
}) {
  const [prompt, setPrompt] = useState('');
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [answer, setAnswer] = useState('');
  const [phase, setPhase] = useState<Phase>({ kind: 'prompt' });
  const [error, setError] = useState<string | null>(null);

  // Two copies on purpose: `brief` is what the user is editing, `original` is
  // what the interview returned, and the difference is what `BriefPanel` shows
  // as provenance.
  const [brief, setBrief] = useState<Brief | null>(null);
  const [original, setOriginal] = useState<Brief | null>(null);
  const [saving, setSaving] = useState(false);

  async function step(nextAnswers: Record<string, string>) {
    setPhase({ kind: 'working' });
    setError(null);
    const result = await advanceInterview(experienceId, {
      prompt,
      answers: nextAnswers,
    });

    if (!result.ok) {
      setError(result.error.message);
      // Back to the question that was on screen, so a refusal or a claims
      // failure is recoverable by retyping rather than by reloading.
      const current = phase.kind === 'question' ? phase : { kind: 'prompt' as const };
      setPhase(current);
      return;
    }

    const { question, brief: produced } = result.value;
    if (produced) {
      setBrief(produced);
      setOriginal(produced);
      onBrief(produced);
      setPhase({ kind: 'prompt' });
      return;
    }
    if (question) {
      setAnswer('');
      setPhase({ kind: 'question', question });
      return;
    }
    // Neither set is a bug in the api, not a state to render around.
    throw new Error('interview returned neither a question nor a brief');
  }

  async function persist() {
    if (!brief) return;
    setSaving(true);
    const result = await saveBrief(experienceId, brief);
    setSaving(false);
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    setError(null);
    setOriginal(result.value);
    onBrief(result.value);
  }

  const working = phase.kind === 'working';

  return (
    <div className="mx-auto max-w-2xl space-y-8 px-6 py-16">
      {/* The prompt box stays put once the interview starts: the answers
          refer back to it, and a first screen that disappears out from under
          someone mid-question is the chat pattern by another route. */}
      <section>
        <h1 className="text-xl font-semibold text-neutral-100">
          What are you launching?
        </h1>
        <textarea
          className="mt-4 w-full resize-y rounded-lg border border-neutral-800 bg-neutral-950 px-4 py-3 text-neutral-100 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none"
          rows={5}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe it in your own words. What you write here is what appears on the page — it is never rewritten."
          aria-label="What are you launching?"
          disabled={working}
        />

        {phase.kind === 'prompt' && !brief && (
          <>
            <button
              type="button"
              className="mt-3 rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 hover:bg-white disabled:opacity-40"
              onClick={() => void step(answers)}
              disabled={working}
            >
              Continue
            </button>
            <p className="mt-6 text-xs text-neutral-500">
              — or start from —{' '}
              {EXAMPLES.map((example, i) => (
                <span key={example}>
                  {i > 0 && ' · '}
                  <button
                    type="button"
                    className="text-neutral-400 underline underline-offset-2 hover:text-neutral-200"
                    onClick={() => setPrompt(`We are announcing ${example}. `)}
                  >
                    {example}
                  </button>
                </span>
              ))}
            </p>
          </>
        )}
      </section>

      {phase.kind === 'question' && (
        <section aria-label="Interview">
          {/* Visible progress, and it is the api's count rather than this
              component's — one definition of how many questions there are. */}
          <p className="text-xs tracking-wide text-neutral-500 uppercase">
            Question {phase.question.index} of {phase.question.total}
          </p>
          <label className="mt-2 block">
            <span className="text-base text-neutral-100">{phase.question.text}</span>
            <input
              className="mt-3 w-full rounded-lg border border-neutral-800 bg-neutral-950 px-4 py-3 text-neutral-100 focus:border-neutral-600 focus:outline-none"
              value={answer}
              autoFocus
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && answer.trim()) {
                  e.preventDefault();
                  submitAnswer();
                }
              }}
            />
          </label>
          <button
            type="button"
            className="mt-3 rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 hover:bg-white disabled:opacity-40"
            onClick={submitAnswer}
            disabled={!answer.trim()}
          >
            Next
          </button>
        </section>
      )}

      {working && <p className="text-sm text-neutral-500">Reading what you wrote…</p>}

      {error && !brief && (
        <p role="alert" className="text-sm text-red-400">
          {error}
        </p>
      )}

      {brief && original && (
        <BriefPanel
          brief={brief}
          original={original}
          onChange={setBrief}
          onSave={() => void persist()}
          saving={saving}
          error={error}
        />
      )}
    </div>
  );

  function submitAnswer() {
    if (phase.kind !== 'question' || !answer.trim()) return;
    const next = { ...answers, [phase.question.field]: answer.trim() };
    setAnswers(next);
    void step(next);
  }
}
