// The first AbstractVisual generator (docs/v1/plan/04-renderer.md); the other
// four joined it in phase 11 and live in `visuals.tsx`. Deterministic: `seed`
// is the only input besides the palette, so the same block renders the same
// visual forever and no user string ever reaches the output
// (security/content-and-web.md).

import type { Color, Palette } from '@/features/art-direction';
import { toCssColor } from '@/features/art-direction';

import type { AbstractVisualProps } from './block-props';
// The PRNG and the intensity scale moved to `visual-seed.ts` in phase 11, when
// four more generators needed them. Five copies of a seeded random is exactly
// the duplication that phase's Search section warns about.
import { INTENSITY, mulberry32 } from './visual-seed';
import { VISUAL_BLEND, visualOpacity } from '../tokens';

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
  return Array.from({ length: INTENSITY[intensity].count }, (_, i) => ({
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
            opacity: visualOpacity(INTENSITY[props.intensity].opacity),
            filter: 'blur(24px)',
            // Light, not paint. Reviewed over a real photograph on
            // /dev/visuals (docs/v1/plan/11-visuals-and-slot.md's "check most
            // likely to be skipped") and this was the one generator that
            // clearly failed it: composited normally, a warm radial gradient
            // over a bright sky reads as a grey-brown smudge — dirt on the
            // lens. `screen` makes the dark part of the gradient transparent
            // so only the light adds, which is what "atmosphere" actually
            // looks like. On the art direction's own dark background it is
            // very nearly a no-op, so this costs the standalone case nothing.
            mixBlendMode: VISUAL_BLEND,
          }}
        />
      ))}
    </div>
  );
}
