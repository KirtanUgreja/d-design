'use client';

// The asset list. Cold 90% — a list, a file input, and the one thing that is
// not decoration: `source`.
//
// "Generated imagery carries different legal and brand risk than an uploaded
// product shot, and a marketer needs to know which is which before
// publishing" (docs/v1/plan/10-brand-and-uploads.md). So it is a visible
// badge on every row rather than a field in a details panel.
//
// **Every asset renders through `<img>`, including SVG.** That is the second
// half of the SVG control and the half that holds even if sanitization missed
// something: referenced through `<img>`, an SVG cannot execute. There is no
// `<object>`, no inline `<svg>`, and no `dangerouslySetInnerHTML` anywhere in
// this file, and there must not be.

import type { Asset } from '@/schema';

/** Assets are served by `api`, which owns object storage — there is exactly
 * one storage path and `web` does not get a second S3 client. The app CSP
 * names this origin in `img-src` for the same reason. */
function assetUrl(storageKey: string): string {
  return `${process.env.NEXT_PUBLIC_API_URL ?? ''}/assets/${storageKey}`;
}

export function AssetList({
  assets,
  onUpload,
  uploading,
  error,
}: {
  assets: Asset[];
  onUpload: (file: File) => void;
  uploading: boolean;
  error: string | null;
}) {
  return (
    <section className="max-w-md space-y-4">
      <header>
        <h2 className="text-sm font-semibold text-neutral-100">Your assets</h2>
        <p className="mt-1 text-xs text-neutral-500">
          Product shots and logos. PNG, JPEG, WEBP, GIF or SVG.
        </p>
      </header>

      <label className="block">
        <span className="sr-only">Upload an asset</span>
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml"
          disabled={uploading}
          aria-label="Upload an asset"
          className="block w-full text-xs text-neutral-400 file:mr-3 file:rounded-md file:border file:border-neutral-700 file:bg-neutral-900 file:px-3 file:py-1.5 file:text-xs file:text-neutral-200"
          onChange={(e) => {
            const file = e.target.files?.[0];
            // `accept` is a convenience for the file picker and nothing more —
            // it is trivially bypassed, which is exactly why the server reads
            // the bytes rather than the type.
            if (file) onUpload(file);
            e.target.value = '';
          }}
        />
      </label>

      {uploading && <p className="text-xs text-neutral-500">Checking that file…</p>}

      {error && (
        <p role="alert" className="text-xs text-amber-300">
          {error}
        </p>
      )}

      {assets.length === 0 ? (
        <p className="text-xs text-neutral-600">Nothing uploaded yet.</p>
      ) : (
        <ul className="space-y-2">
          {assets.map((asset) => (
            <li
              key={asset.id}
              className="flex items-center gap-3 rounded-md border border-neutral-800 p-2"
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- the
                  control, not an oversight: next/image would route an SVG
                  through the optimizer, which is the CPU-exhaustion path
                  docs/security/content-and-web.md says to keep SVG out of. */}
              <img
                src={assetUrl(asset.storageKey)}
                alt={asset.alt ?? ''}
                width={40}
                height={40}
                className="h-10 w-10 shrink-0 rounded object-cover"
              />
              <span className="min-w-0 flex-1 truncate text-xs text-neutral-300">
                {asset.alt || asset.mime}
                {asset.width && asset.height && (
                  <span className="text-neutral-600">
                    {' '}
                    {asset.width}×{asset.height}
                  </span>
                )}
              </span>
              <Source source={asset.source} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Uploaded or generated, said plainly. The one field on this row a marketer
 * has to check before publishing. */
function Source({ source }: { source: Asset['source'] }) {
  const generated = source === 'generated';
  return (
    <span
      className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] tracking-wide uppercase ${
        generated ? 'bg-amber-950/60 text-amber-300' : 'bg-neutral-800 text-neutral-400'
      }`}
    >
      {generated ? 'generated' : 'yours'}
    </span>
  );
}
