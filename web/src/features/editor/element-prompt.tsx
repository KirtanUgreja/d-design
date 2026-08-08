'use client';

// The element-scoped prompt: inline, under the selection, always in the same
// place, and only ever present when something is selected
// (docs/v1/plan/09-editor.md -> "The canvas is true scale, always"). An
// always-present prompt box invites page-level requests the patch shape cannot
// serve, and a request the shape cannot serve is a promise the product breaks.

import { useState } from 'react';

import type { EditResult } from '@/schema';

export function ElementPrompt({
  onSubmit,
  pending,
  result,
  error,
}: {
  onSubmit: (instruction: string) => void;
  pending: boolean;
  /** The last response. A refusal is a successful response with copy in it,
   * not an error — which is why it renders as an answer rather than in red. */
  result: EditResult | null;
  error: string | null;
}) {
  const [instruction, setInstruction] = useState('');

  function submit() {
    const trimmed = instruction.trim();
    if (!trimmed || pending) return;
    onSubmit(trimmed);
  }

  return (
    <div className="mt-1 w-full max-w-md">
      <div className="flex gap-1.5">
        <input
          className="flex-1 rounded-md border border-neutral-700 bg-neutral-950/95 px-2.5 py-1.5 text-sm text-neutral-100 placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
          value={instruction}
          placeholder="Change this element…"
          aria-label="Edit this element"
          disabled={pending}
          onChange={(e) => setInstruction(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              submit();
            }
          }}
        />
        <button
          type="button"
          className="rounded-md bg-neutral-100 px-3 py-1.5 text-sm font-medium text-neutral-900 disabled:opacity-40"
          onClick={submit}
          disabled={pending || !instruction.trim()}
        >
          {pending ? '…' : 'Go'}
        </button>
      </div>

      {/* A refusal is the product's answer, so it is typeset as one: plain,
          addressed to the user, offering what to do instead. Not red, not an
          alert, not a stack trace. */}
      {result?.refusal && (
        <p className="mt-1.5 rounded-md border border-neutral-800 bg-neutral-950/95 px-2.5 py-2 text-xs text-neutral-300">
          {result.refusal}
        </p>
      )}

      {error && (
        <p role="alert" className="mt-1.5 text-xs text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
