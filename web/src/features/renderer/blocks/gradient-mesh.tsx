// The one AbstractVisual generator this phase ships (docs/v1/plan/04-renderer.md
// — the other four land in phase 11). Deterministic: `seed` is the only input
// besides the palette, so the same block renders the same visual forever and
// no user string ever reaches the output (security/content-and-web.md).

import type { Color, Palette } from '@/features/art-direction';
import { toCssColor } from '@/features/art-direction';

import type { AbstractVisualProps } from './block-props';

// mulberry32 — a tiny, fast, seedable PRNG. Not cryptographic, and does not
// need to be: this seeds visual placement, not a security decision.
function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const BLOB_COUNT: Record<AbstractVisualProps['intensity'], number> = {
  subtle: 2,
  medium: 3,
  bold: 4,
};

const OPACITY: Record<AbstractVisualProps['intensity'], number> = {
  subtle: 0.25,
  medium: 0.45,
  bold: 0.7,
};

interface Blob {
  color: Color;
  leftPct: number;
  topPct: number;
  sizePct: number;
}

function blobs(
  seed: number,
  intensity: AbstractVisualProps['intensity'],
  palette: Palette,
): Blob[] {
  const rand = mulberry32(seed);
  const colors = [palette.accent, palette.accentSoft, palette.bgElevated];
  return Array.from({ length: BLOB_COUNT[intensity] }, (_, i) => ({
    color: colors[i % colors.length] ?? palette.accent,
    leftPct: 10 + rand() * 80,
    topPct: 10 + rand() * 80,
    sizePct: 40 + rand() * 50,
  }));
}

export function GradientMesh({
  props,
  palette,
}: {
  props: AbstractVisualProps;
  palette: Palette;
}) {
  return (
    <div
      style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}
      aria-hidden="true"
    >
      {blobs(props.seed, props.intensity, palette).map((b, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${b.leftPct}%`,
            top: `${b.topPct}%`,
            inlineSize: `${b.sizePct}%`,
            blockSize: `${b.sizePct}%`,
            transform: 'translate(-50%, -50%)',
            borderRadius: '50%',
            background: `radial-gradient(circle, ${toCssColor(b.color)} 0%, transparent 70%)`,
            opacity: OPACITY[props.intensity],
            filter: 'blur(24px)',
          }}
        />
      ))}
    </div>
  );
}
