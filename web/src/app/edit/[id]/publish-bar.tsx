'use client';

// The publish reveal — docs/design/app.md's third hot surface, "the one that
// gets screenshotted into Slack".
//
// Two states in one component because they are two halves of one gesture: the
// bar is the invitation, the reveal is the answer. Splitting them into two
// files would put the thing being revealed a directory away from the thing
// that reveals it.
//
// What the design doc asks for, and what each line here is:
//   · the live URL, large and copyable          -> the <a>, at display size
//   · the real page behind it                   -> an overlay, not a redirect;
//     the editor stays where it was, dimmed, and closing puts you back in it
//   · one click to open, one to embed           -> the two buttons under it
//   · republishing is explicit                  -> the bar says "Publish
//     changes" once something is live; nothing republishes on edit
//   · unpublish is instant and real             -> it is, and it is offered
//     right here rather than hidden in a settings page. The half that makes
//     the first half feel safe
//
// Deliberately not here: the OG-image screenshot and the unfurl check. Both are
// phase 05's recorded deferrals and both need Playwright in a job, not a
// button.

import { useState } from 'react';

const BUTTON =
  'rounded-md border border-neutral-700 px-3 py-1.5 text-sm text-neutral-200 transition-colors hover:border-neutral-500 hover:text-white disabled:opacity-40';

function embedCode(origin: string, id: string): string {
  return `<iframe src="${origin}/e/${id}" width="100%" height="640" style="border:0" allowfullscreen></iframe>`;
}

export function PublishBar({
  id,
  title,
  publishable,
  published,
  pending,
  error,
  onPublish,
  onUnpublish,
  onDismiss,
}: {
  id: string;
  title: string;
  /** False for the fixture-backed editor — there is nothing stored to publish. */
  publishable: boolean;
  /** The reveal is showing. Null until this session has published something:
   * a page that was already live before you opened the editor does not get
   * the reveal, it gets "Publish changes". */
  published: boolean;
  pending: boolean;
  error: string | null;
  onPublish: () => void;
  onUnpublish: () => void;
  onDismiss: () => void;
}) {
  const [copied, setCopied] = useState<'link' | 'embed' | null>(null);
  // `window` at click time, never at render time — this component is rendered
  // on the server first, and an origin read during render is a hydration
  // mismatch waiting for the first deployment that is not localhost.
  const copy = (what: 'link' | 'embed') => {
    const origin = window.location.origin;
    void navigator.clipboard
      .writeText(what === 'link' ? `${origin}/p/${id}` : embedCode(origin, id))
      .then(() => setCopied(what));
  };

  return (
    <>
      <header className="flex shrink-0 items-center justify-between border-b border-neutral-800 px-4 py-2.5">
        <h1 className="truncate text-sm font-medium text-neutral-300">{title}</h1>
        <div className="flex items-center gap-3">
          {error && (
            <span role="alert" className="text-xs text-red-400">
              {error}
            </span>
          )}
          {!publishable && (
            <span className="text-xs text-neutral-500">
              a sample experience — nothing to publish
            </span>
          )}
          <button
            type="button"
            className="rounded-md bg-neutral-100 px-3 py-1.5 text-sm font-medium text-neutral-900 transition-colors hover:bg-white disabled:opacity-40"
            disabled={!publishable || pending}
            onClick={onPublish}
          >
            {pending ? 'Publishing…' : published ? 'Publish changes' : 'Publish'}
          </button>
        </div>
      </header>

      {published && (
        // The editor stays visible behind this, which is the point — you are
        // looking at the thing you just shipped, not at a success page.
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/80 backdrop-blur-sm">
          <div className="mx-6 w-full max-w-2xl rounded-xl border border-neutral-800 bg-neutral-900 p-8 shadow-2xl">
            <p className="text-xs tracking-wide text-neutral-500 uppercase">Live</p>
            <a
              href={`/p/${id}`}
              target="_blank"
              rel="noreferrer"
              className="mt-3 block font-mono text-xl break-all text-neutral-100 underline decoration-neutral-600 underline-offset-4 hover:decoration-neutral-300"
            >
              /p/{id}
            </a>

            <div className="mt-6 flex flex-wrap items-center gap-2">
              <a href={`/p/${id}`} target="_blank" rel="noreferrer" className={BUTTON}>
                Open
              </a>
              <button type="button" className={BUTTON} onClick={() => copy('link')}>
                {copied === 'link' ? 'Copied' : 'Copy link'}
              </button>
              <button type="button" className={BUTTON} onClick={() => copy('embed')}>
                {copied === 'embed' ? 'Copied' : 'Copy embed code'}
              </button>
              <button
                type="button"
                className={`${BUTTON} ml-auto`}
                disabled={pending}
                onClick={onUnpublish}
              >
                Unpublish
              </button>
              <button type="button" className={BUTTON} onClick={onDismiss}>
                Back to editing
              </button>
            </div>

            <p className="mt-6 text-xs text-neutral-500">
              Editing does not change the live page. Publish again when you want it to.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
