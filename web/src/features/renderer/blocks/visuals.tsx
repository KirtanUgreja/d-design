// The four AbstractVisual generators that join `gradient-mesh`
// (docs/v1/plan/11-visuals-and-slot.md). Rendered as code — CSS and SVG,
// using art-direction colours — so they cost no assets, are always on brand,
// and regenerate identically from a seed.
//
// **This is what makes a sparse scene look designed rather than empty**, and
// it is the cheapest visual quality in the product.
//
// Every one of them obeys the same three rules the phase doc sets: the seed is
// the only variable input, no user string reaches the output, and each has to
// survive sitting behind a real photograph without fighting it. That last one
// is why they are all quiet by default and why `bold` tops out where it does —
// an abstract visual that looks impressive alone and ruins a product shot is a
// worse generator than a dull one.
//
// **Every layer composites with `mix-blend-mode: screen`**, which is the single
// change that made the photography review pass. Composited normally these are
// paint: a warm gradient over a bright sky darkens it into a grey-brown smudge.
// With `screen` the dark part of a layer is transparent and only the light
// adds, so a generator reads as lighting rather than as graphics. Over the art
// direction's own near-black background it is very nearly a no-op, so the
// standalone case pays nothing for it.

import type { Color, Palette } from '@/features/art-direction';
import { toCssColor } from '@/features/art-direction';

import type { AbstractVisualProps } from './block-props';
import { INTENSITY, mulberry32, type Intensity } from './visual-seed';

/** Every generator paints inside the same absolutely-positioned, non-
 * interactive layer. `aria-hidden` because none of them carries meaning — a
 * screen reader announcing "decorative gradient" is noise. */
function Layer({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}
      aria-hidden="true"
    >
      {children}
    </div>
  );
}

function accents(palette: Palette): Color[] {
  return [palette.accent, palette.accentSoft, palette.bgElevated];
}

// --- particle-field --------------------------------------------------------

/** Scattered points of light. Reads as depth rather than as pattern, which is
 * what lets it sit behind a photograph — the eye takes it for lens bokeh and
 * stops looking. Counts scale well past the other generators because a
 * particle carries far less weight than a blob. */
export function ParticleField({
  props,
  palette,
}: {
  props: AbstractVisualProps;
  palette: Palette;
}) {
  const rand = mulberry32(props.seed);
  const { count, opacity } = INTENSITY[props.intensity];
  const colors = accents(palette);
  const particles = Array.from({ length: count * 18 }, (_, i) => ({
    left: rand() * 100,
    top: rand() * 100,
    size: 1 + rand() * 3,
    dim: 0.2 + rand() * 0.8,
    color: colors[i % colors.length] ?? palette.accent,
  }));

  return (
    <Layer>
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${p.left}%`,
            top: `${p.top}%`,
            inlineSize: `${p.size}px`,
            blockSize: `${p.size}px`,
            borderRadius: '50%',
            background: toCssColor(p.color),
            opacity: opacity * p.dim,
            filter: 'blur(0.5px)',
            mixBlendMode: 'screen',
          }}
        />
      ))}
    </Layer>
  );
}

// --- grid-lines ------------------------------------------------------------

/** An architectural grid, faded at the edges. The most structural of the five
 * and the one most likely to fight a photograph, so it is masked to the centre
 * and never reaches full strength at the frame. */
export function GridLines({
  props,
  palette,
}: {
  props: AbstractVisualProps;
  palette: Palette;
}) {
  const rand = mulberry32(props.seed);
  const { count, opacity } = INTENSITY[props.intensity];
  const spacing = 42 + Math.floor(rand() * 40);
  const skew = -6 + rand() * 12;
  const line = toCssColor(palette.accentSoft);

  return (
    <Layer>
      <div
        style={{
          position: 'absolute',
          inset: '-25%',
          transform: `rotate(${skew.toFixed(2)}deg)`,
          backgroundImage: `linear-gradient(to right, ${line} 1px, transparent 1px), linear-gradient(to bottom, ${line} 1px, transparent 1px)`,
          backgroundSize: `${spacing}px ${spacing}px`,
          opacity: opacity * 0.5,
          mixBlendMode: 'screen',
          // Fades the grid out before it reaches any edge, so it never draws a
          // hard line across a photograph behind it.
          maskImage: 'radial-gradient(ellipse at center, black 20%, transparent 75%)',
          WebkitMaskImage:
            'radial-gradient(ellipse at center, black 20%, transparent 75%)',
        }}
      />
      {Array.from({ length: count }, (_, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${rand() * 100}%`,
            top: 0,
            bottom: 0,
            inlineSize: '1px',
            background: `linear-gradient(to bottom, transparent, ${toCssColor(palette.accent)}, transparent)`,
            opacity: opacity * 0.6,
            mixBlendMode: 'screen',
          }}
        />
      ))}
    </Layer>
  );
}

// --- orb -------------------------------------------------------------------

/** One light source, off centre. The quietest generator and the safest behind
 * photography — a single soft falloff reads as lighting rather than as
 * graphics, which is exactly what a product shot wants behind it. */
export function Orb({
  props,
  palette,
}: {
  props: AbstractVisualProps;
  palette: Palette;
}) {
  const rand = mulberry32(props.seed);
  const { opacity } = INTENSITY[props.intensity];
  const left = 20 + rand() * 60;
  const top = 15 + rand() * 50;
  const size = 55 + rand() * 45;

  return (
    <Layer>
      <div
        style={{
          position: 'absolute',
          left: `${left}%`,
          top: `${top}%`,
          inlineSize: `${size}%`,
          blockSize: `${size}%`,
          transform: 'translate(-50%, -50%)',
          borderRadius: '50%',
          background: `radial-gradient(circle, ${toCssColor(palette.accent)} 0%, ${toCssColor(palette.accentSoft)} 35%, transparent 70%)`,
          opacity,
          filter: 'blur(40px)',
          mixBlendMode: 'screen',
        }}
      />
      {/* A faint rim, so the orb has an edge to catch rather than dissolving
          entirely into the background at low intensity. */}
      <div
        style={{
          position: 'absolute',
          left: `${left}%`,
          top: `${top}%`,
          inlineSize: `${size * 0.55}%`,
          blockSize: `${size * 0.55}%`,
          transform: 'translate(-50%, -50%)',
          borderRadius: '50%',
          border: `1px solid ${toCssColor(palette.accentSoft)}`,
          opacity: opacity * 0.35,
          filter: 'blur(1px)',
          mixBlendMode: 'screen',
        }}
      />
    </Layer>
  );
}

// --- noise-veil ------------------------------------------------------------

/** Turbulence over a wash of accent. The scene already lays a fixed grain over
 * everything (`scene.tsx`); this is the *seeded, per-block* version — a
 * different `baseFrequency` and a tint, so the two do not simply double up.
 *
 * The SVG is a `data:` URI with no user input in it: the only interpolated
 * value is a number this file computed. */
export function NoiseVeil({
  props,
  palette,
}: {
  props: AbstractVisualProps;
  palette: Palette;
}) {
  const rand = mulberry32(props.seed);
  const { opacity } = INTENSITY[props.intensity];
  const frequency = (0.35 + rand() * 0.5).toFixed(2);
  const angle = Math.floor(rand() * 360);

  return (
    <Layer>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(${angle}deg, ${toCssColor(palette.accentSoft)} 0%, transparent 60%)`,
          opacity: opacity * 0.8,
          mixBlendMode: 'screen',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='128' height='128'%3E%3Cfilter id='v'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='${frequency}' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23v)'/%3E%3C/svg%3E")`,
          opacity: opacity * 0.35,
          mixBlendMode: 'overlay',
        }}
      />
    </Layer>
  );
}

export type { Intensity };
