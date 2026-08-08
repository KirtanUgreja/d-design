'use client';

// The approved-claims record, visible and editable, permanently
// (docs/v1/plan/08-intake.md -> "The interview is not a chat").
//
// This panel is the product's answer to Risk 2. The phase doc is blunt about
// why it cannot be a step the user passes through and leaves behind: key
// messages and proof points are APPROVED COPY, and "the Intake UI's job here
// is narrow and important: make it obvious that what the user types into
// keyMessages is what will appear on the page." A brief the user cannot see
// after generating is a claim they cannot check.
//
// Provenance is shown per claim — `yours` vs `selected by the interview` —
// which docs/design/app.md calls "the trust feature this product has and its
// competitors do not". It is honest by construction rather than by labelling:
// the interview may only select and split the user's own words
// (api/features/intake/checks.py rejects anything else), so every claim here
// traces to something the user typed, and editing one makes it theirs
// outright.
//
// Tailwind, not art-direction tokens: this is app chrome, and no file imports
// both (docs/techstack/frontend.md).

import type { Brief } from '@/schema';

/** 3-5, matching `key_messages` on the Pydantic model. Restated as a constant
 * rather than reached for by hand at each call site — the generated Zod schema
 * enforces it, this only decides when to grey a button out. */
const MIN_KEY_MESSAGES = 3;
const MAX_KEY_MESSAGES = 5;

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium tracking-wide text-neutral-400 uppercase">
        {label}
      </span>
      {hint && <span className="mt-0.5 block text-xs text-neutral-500">{hint}</span>}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

const INPUT =
  'w-full rounded-md border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm ' +
  'text-neutral-100 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none';

export function BriefPanel({
  brief,
  original,
  onChange,
  onSave,
  saving,
  error,
}: {
  brief: Brief;
  /** What the interview produced, kept alongside the working copy so a claim
   * the user has since edited can be shown as theirs. */
  original: Brief;
  onChange: (brief: Brief) => void;
  onSave: () => void;
  saving: boolean;
  error: string | null;
}) {
  const dirty = JSON.stringify(brief) !== JSON.stringify(original);
  // `proofPoints` has a default on the Pydantic model, so it generates as
  // optional and arrives as `string[] | undefined`. Normalized once here
  // rather than `?? []` at six call sites.
  const proofPoints = brief.proofPoints ?? [];
  const originalProofPoints = original.proofPoints ?? [];

  function setMessage(index: number, text: string) {
    onChange({
      ...brief,
      keyMessages: brief.keyMessages.map((m, i) => (i === index ? text : m)),
    });
  }

  function setProof(index: number, text: string) {
    onChange({
      ...brief,
      proofPoints: proofPoints.map((p, i) => (i === index ? text : p)),
    });
  }

  return (
    <section
      className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-5"
      aria-label="Brief"
    >
      <header className="mb-4">
        <h2 className="text-sm font-semibold text-neutral-100">Your brief</h2>
        <p className="mt-1 text-xs text-neutral-500">
          These exact words are what appears on the page. Nothing here is rewritten later
          — edit anything that is not how you would say it.
        </p>
      </header>

      <div className="space-y-4">
        <Field label="Goal">
          <input
            className={INPUT}
            value={brief.goal}
            onChange={(e) => onChange({ ...brief, goal: e.target.value })}
          />
        </Field>

        <Field label="Audience">
          <input
            className={INPUT}
            value={brief.audience}
            onChange={(e) => onChange({ ...brief, audience: e.target.value })}
          />
        </Field>

        <fieldset>
          <legend className="text-xs font-medium tracking-wide text-neutral-400 uppercase">
            Key messages
          </legend>
          <p className="mt-0.5 text-xs text-neutral-500">
            {MIN_KEY_MESSAGES}–{MAX_KEY_MESSAGES}. Approved copy — arranged on the page,
            never rewritten.
          </p>
          <ul className="mt-1.5 space-y-2">
            {brief.keyMessages.map((message, index) => (
              <li key={index}>
                <textarea
                  className={`${INPUT} resize-y`}
                  rows={2}
                  value={message}
                  onChange={(e) => setMessage(index, e.target.value)}
                  aria-label={`Key message ${index + 1}`}
                />
                <div className="mt-1 flex items-center justify-between">
                  <Provenance
                    edited={message !== original.keyMessages[index]}
                    kind="message"
                  />
                  {brief.keyMessages.length > MIN_KEY_MESSAGES && (
                    <button
                      type="button"
                      className="text-xs text-neutral-500 hover:text-neutral-300"
                      onClick={() =>
                        onChange({
                          ...brief,
                          keyMessages: brief.keyMessages.filter((_, i) => i !== index),
                        })
                      }
                    >
                      remove
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          {brief.keyMessages.length < MAX_KEY_MESSAGES && (
            <button
              type="button"
              className="mt-2 text-xs text-neutral-400 hover:text-neutral-200"
              onClick={() =>
                onChange({ ...brief, keyMessages: [...brief.keyMessages, ''] })
              }
            >
              + add a message
            </button>
          )}
        </fieldset>

        <fieldset>
          <legend className="text-xs font-medium tracking-wide text-neutral-400 uppercase">
            Proof points
          </legend>
          <p className="mt-0.5 text-xs text-neutral-500">
            Statistics, quotes, customer names. Only what you can stand behind.
          </p>
          <ul className="mt-1.5 space-y-2">
            {proofPoints.map((proof, index) => (
              <li key={index}>
                <input
                  className={INPUT}
                  value={proof}
                  onChange={(e) => setProof(index, e.target.value)}
                  aria-label={`Proof point ${index + 1}`}
                />
                <div className="mt-1 flex items-center justify-between">
                  <Provenance
                    edited={proof !== originalProofPoints[index]}
                    kind="proof point"
                  />
                  <button
                    type="button"
                    className="text-xs text-neutral-500 hover:text-neutral-300"
                    onClick={() =>
                      onChange({
                        ...brief,
                        proofPoints: proofPoints.filter((_, i) => i !== index),
                      })
                    }
                  >
                    remove
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="mt-2 text-xs text-neutral-400 hover:text-neutral-200"
            onClick={() => onChange({ ...brief, proofPoints: [...proofPoints, ''] })}
          >
            + add a proof point
          </button>
        </fieldset>

        <Field label="Tone">
          <input
            className={INPUT}
            value={brief.tone}
            onChange={(e) => onChange({ ...brief, tone: e.target.value })}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Button">
            <input
              className={INPUT}
              value={brief.cta.label}
              onChange={(e) =>
                onChange({ ...brief, cta: { ...brief.cta, label: e.target.value } })
              }
            />
          </Field>
          <Field label="Links to">
            <input
              className={INPUT}
              value={brief.cta.href}
              onChange={(e) =>
                onChange({ ...brief, cta: { ...brief.cta, href: e.target.value } })
              }
            />
          </Field>
        </div>

        <Field label="Constraints" hint="Anything that must not be said, or must be.">
          <textarea
            className={`${INPUT} resize-y`}
            rows={2}
            value={brief.constraints ?? ''}
            onChange={(e) => onChange({ ...brief, constraints: e.target.value || null })}
          />
        </Field>
      </div>

      {error && (
        <p role="alert" className="mt-4 text-xs text-red-400">
          {error}
        </p>
      )}

      <div className="mt-5 flex items-center gap-3">
        <button
          type="button"
          className="rounded-md border border-neutral-700 px-3 py-1.5 text-xs text-neutral-200 hover:border-neutral-500 disabled:opacity-40"
          onClick={onSave}
          disabled={!dirty || saving}
        >
          {saving ? 'Saving…' : 'Save brief'}
        </button>
        {dirty && !saving && (
          <span className="text-xs text-neutral-500">unsaved changes</span>
        )}
      </div>
    </section>
  );
}

/** Two states, and the wording is the point. "Your words" is the honest label
 * for both — the interview is only allowed to select and split what the user
 * typed — so the distinction shown is whether the user has since touched it,
 * not whether the claim was invented, because an invented one never gets
 * this far. */
function Provenance({ edited, kind }: { edited: boolean; kind: string }) {
  return (
    <span className="text-xs text-neutral-600">
      {edited ? `edited — your ${kind}` : 'your words, taken from what you typed'}
    </span>
  );
}
