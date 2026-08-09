// The judgment surface for the five AbstractVisual generators
// (docs/v1/plan/11-visuals-and-slot.md -> Verify). The phase doc calls the
// photography check "the check most likely to be skipped", so this page makes
// skipping it require effort: the same grid is rendered twice, once on the
// art direction's own background and once layered over a real uploaded
// photograph.
//
// **Why a photograph specifically.** docs/v1/art-direction.md names it: an
// abstract visual can look excellent alone and fight a product shot badly.
// Fighting looks like a grid drawing lines across a subject's face, or a
// gradient mesh competing with the photo's own light. On a flat background
// none of that is visible, which is exactly why a page without the photo half
// would pass while telling you nothing.
//
// Dev-only, never linked. The asset id is read from the live `assets` list, so
// this works with whatever the developer has actually uploaded rather than
// depending on a checked-in binary.

import type { CSSProperties } from 'react';

import { toCssVars } from '@/features/art-direction';
import { seededArtDirection } from '@/features/art-direction/server';
import { AbstractVisualBlock } from '@/features/renderer';

const GENERATORS = [
  'halftone-field',
  'particle-field',
  'grid-lines',
  'hatch-drift',
  'dither-fade',
  'block-collage',
] as const;
const INTENSITIES = ['subtle', 'medium', 'bold'] as const;

async function firstPhoto(): Promise<string | null> {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) return null;
  try {
    const res = await fetch(`${base}/assets`, { cache: 'no-store' });
    if (!res.ok) return null;
    const assets: unknown = await res.json();
    if (!Array.isArray(assets)) return null;
    const photo = assets.find(
      (a): a is { storageKey: string; mime: string } =>
        typeof a === 'object' &&
        a !== null &&
        'mime' in a &&
        (a as { mime: unknown }).mime === 'image/jpeg',
    );
    return photo ? `${base}/assets/${photo.storageKey}` : null;
  } catch {
    return null;
  }
}

function Cell({
  generator,
  intensity,
  photo,
}: {
  generator: (typeof GENERATORS)[number];
  intensity: (typeof INTENSITIES)[number];
  photo: string | null;
}) {
  return (
    <div
      style={{
        position: 'relative',
        aspectRatio: '16 / 10',
        overflow: 'hidden',
        borderRadius: 8,
        background: photo ? `url(${photo}) center/cover` : 'var(--bg)',
      }}
    >
      <AbstractVisualBlock
        props={{ type: 'abstract-visual', generator, intensity, seed: 20260809 }}
      />
      <span
        style={{
          position: 'absolute',
          insetInlineStart: 8,
          insetBlockEnd: 6,
          font: '500 11px/1 ui-monospace, monospace',
          color: 'var(--ink)',
          background: 'rgba(0,0,0,.55)',
          padding: '4px 6px',
          borderRadius: 4,
        }}
      >
        {generator} · {intensity}
      </span>
    </div>
  );
}

function Grid({ photo, title }: { photo: string | null; title: string }) {
  return (
    <section style={{ marginBlockEnd: 48 }}>
      <h2 style={{ font: '600 14px/1.4 ui-monospace, monospace', marginBlockEnd: 12 }}>
        {title}
      </h2>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 12,
        }}
      >
        {GENERATORS.flatMap((generator) =>
          INTENSITIES.map((intensity) => (
            <Cell
              key={`${generator}-${intensity}`}
              generator={generator}
              intensity={intensity}
              photo={photo}
            />
          )),
        )}
      </div>
    </section>
  );
}

export default async function VisualsReviewPage() {
  const photo = await firstPhoto();
  return (
    <main
      style={
        {
          ...toCssVars(seededArtDirection('cinematic-dark').artDirection),
          background: 'var(--bg)',
          color: 'var(--ink)',
          minBlockSize: '100vh',
          padding: 24,
        } as CSSProperties
      }
    >
      <Grid photo={null} title="On the art direction's own background" />
      {photo ? (
        <Grid photo={photo} title="Over a real uploaded photograph" />
      ) : (
        <p style={{ font: '400 13px/1.5 ui-monospace, monospace', opacity: 0.7 }}>
          Upload a JPEG at /brand to see the photography half of this review — which is
          the half that actually catches a generator fighting an image.
        </p>
      )}
    </main>
  );
}
