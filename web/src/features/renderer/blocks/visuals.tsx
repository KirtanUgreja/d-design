// The six AbstractVisual generators (docs/v2/plan/14-texture-without-gradient.md,
// replacing the five of docs/v1/plan/11-visuals-and-slot.md). Rendered as code
// — CSS and SVG masks, using art-direction colours — so they cost no assets,
// are always on brand, and regenerate identically from a seed.
//
// **This is what makes a sparse scene look designed rather than empty**, and
// it is the cheapest visual quality in the product.
//
// Phase 14 rewrote the paint and left the determinism alone. Four of the five
// v1 generators were built out of gradient functions and two of them also
// carried a `blur()`, which is the artifact breaking principle 5 — the rule
// was filed under `docs/design/` and read as being about our own chrome.
// What replaces them is the same colours carried by dot, line, dither and
// hard edge.
//
// Three properties survive unchanged and are the reason this file is safe:
// the seed is the only variable input, no user string reaches the output, and
// every generator has to survive sitting behind a real photograph without
// fighting it. `visual-seed.ts` — one PRNG, one intensity scale — is untouched.
//
// **Colour is a token reference, never a resolved value.** v1 called
// `toCssColor(palette.accent)` here, which turned a token into a string
// outside the one file allowed to. These read `COLOR_VAR`, so the generators
// no longer need the palette at all.

import { COLOR_VAR, type ColorRole } from '@/features/art-direction';

import type { AbstractVisualProps } from './block-props';
import { INTENSITY, mulberry32, type Intensity } from './visual-seed';
import * as PATTERN from '../texture/patterns';
import { VISUAL_BLEND, visualOpacity } from '../tokens';

/** Every generator paints inside the same absolutely-positioned, non-
 * interactive layer. `aria-hidden` because none of them carries meaning — a
 * screen reader announcing "decorative pattern" is noise. */
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

/** The three roles a generator is allowed to paint with. Same set as v1, as
 * references rather than values. */
const ROLES: readonly ColorRole[] = ['accent', 'accentSoft', 'bgElevated'];

const roleAt = (i: number): string => COLOR_VAR[ROLES[i % ROLES.length] ?? 'accent'];

/** A masked patch of one colour. The single shape every generator below is
 * built from — no generator writes a `background` other than a flat token
 * colour, which is what makes the no-gradient rule hold by construction here
 * rather than by review. */
function Patch({
  mask,
  scale,
  color,
  opacity,
  rotate,
  style,
}: {
  mask: string;
  scale: number;
  color: string;
  opacity: string;
  rotate?: number;
  style?: React.CSSProperties;
}) {
  return (
    <div
      style={{
        position: 'absolute',
        backgroundColor: color,
        maskImage: mask,
        WebkitMaskImage: mask,
        maskRepeat: 'repeat',
        WebkitMaskRepeat: 'repeat',
        maskSize: `${scale}px ${scale}px`,
        WebkitMaskSize: `${scale}px ${scale}px`,
        opacity,
        mixBlendMode: VISUAL_BLEND,
        ...(rotate === undefined ? {} : { transform: `rotate(${rotate.toFixed(2)}deg)` }),
        ...style,
      }}
    />
  );
}

// --- halftone-field (was gradient-mesh) -------------------------------------

/** Stepped dot clusters, seeded. The direct replacement for the four blurred
 * radial blobs, and the generator the phase doc singles out: a cluster is a
 * hard-edged ellipse of dots at one density, so overlapping clusters build
 * depth in discrete steps instead of a ramp. */
export function HalftoneField({ props }: { props: AbstractVisualProps }) {
  const rand = mulberry32(props.seed);
  const { count, opacity } = INTENSITY[props.intensity];
  const clusters = Array.from({ length: count }, (_, i) => ({
    left: 10 + rand() * 80,
    top: 10 + rand() * 80,
    size: 40 + rand() * 50,
    // 1..3, never 4. At cluster size the densest band stops reading as a dot
    // lattice and becomes a fill, which is a blob with extra steps.
    density: (1 + Math.floor(rand() * 3)) as PATTERN.Density,
    angle: rand() * 90,
    color: roleAt(i),
  }));

  return (
    <Layer>
      {clusters.map((c, i) => (
        <Patch
          key={i}
          mask={PATTERN.halftone(c.density)}
          scale={4 + c.density}
          color={c.color}
          opacity={visualOpacity(opacity * 0.7)}
          rotate={c.angle}
          style={{
            left: `${c.left}%`,
            top: `${c.top}%`,
            inlineSize: `${c.size}%`,
            blockSize: `${c.size}%`,
            clipPath: 'ellipse(50% 50% at 50% 50%)',
            translate: '-50% -50%',
          }}
        />
      ))}
    </Layer>
  );
}

// --- hatch-drift (was orb) --------------------------------------------------

/** An engraved line field. `orb` was a two-stop radial gradient under a 40px
 * blur — a light source, which is precisely the effect rule 19 bans. This
 * reads as depth the way an engraving does: overlapping line panels at
 * different angles and spacings, nothing luminous anywhere. */
export function HatchDrift({ props }: { props: AbstractVisualProps }) {
  const rand = mulberry32(props.seed);
  const { count, opacity } = INTENSITY[props.intensity];
  const panels = Array.from({ length: count }, (_, i) => ({
    left: rand() * 60,
    top: rand() * 55,
    size: 45 + rand() * 45,
    angle: -60 + rand() * 120,
    spacing: 6 + rand() * 8,
    density: (1 + Math.floor(rand() * 2)) as PATTERN.Density,
    color: roleAt(i),
  }));

  return (
    <Layer>
      {panels.map((p, i) => (
        <Patch
          key={i}
          mask={PATTERN.hatch(p.density, false)}
          scale={p.spacing}
          color={p.color}
          opacity={visualOpacity(opacity * 0.8)}
          rotate={p.angle}
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            inlineSize: `${p.size}%`,
            blockSize: `${p.size}%`,
          }}
        />
      ))}
    </Layer>
  );
}

// --- dither-fade (was noise-veil) -------------------------------------------

/** A Bayer dissolve across the frame. `noise-veil` was a linear gradient with
 * turbulence over it; this is the same idea done as ordered dithering, which
 * is what a dissolve looks like when it is printed rather than composited.
 *
 * Bands are drawn as non-overlapping vertical strips because Bayer levels
 * nest — stacking them yields the densest one everywhere, which is a flat
 * field. The same reason `DitherVignette` uses rings. */
export function DitherFade({ props }: { props: AbstractVisualProps }) {
  const rand = mulberry32(props.seed);
  const { opacity } = INTENSITY[props.intensity];
  const steps = 4;
  const fromLeft = rand() > 0.5;
  const color = roleAt(Math.floor(rand() * ROLES.length));

  return (
    <Layer>
      {Array.from({ length: steps }, (_, band) => {
        const density = (fromLeft ? steps - band : band + 1) as PATTERN.Density;
        const start = (band * 100) / steps;
        return (
          <Patch
            key={band}
            mask={PATTERN.dither(PATTERN.DITHER_LEVEL[density])}
            scale={4}
            color={color}
            opacity={visualOpacity(opacity)}
            style={{
              insetBlock: 0,
              insetInlineStart: `${start}%`,
              inlineSize: `${100 / steps}%`,
            }}
          />
        );
      })}
    </Layer>
  );
}

// --- grid-lines (kept) ------------------------------------------------------

/** An architectural grid. Kept from v1; its paint changed twice over.
 *
 * The grid itself was two `linear-gradient`s faking 1px rules, and its edge
 * fade was a `radial-gradient` mask. The rules are now a cross-hatch mask, and
 * the fade is a hard inset frame.
 *
 * ponytail: the v1 fade existed so the grid never draws a hard line across a
 * photograph, and a hard frame is a different answer rather than a strictly
 * better one. The ceiling is that over a busy image the frame edge may read as
 * an artifact; the upgrade path is the stepped ring bands `DitherVignette`
 * already implements. Left until the photography review says it is needed. */
export function GridLines({ props }: { props: AbstractVisualProps }) {
  const rand = mulberry32(props.seed);
  const { count, opacity } = INTENSITY[props.intensity];
  const spacing = 42 + Math.floor(rand() * 40);
  const skew = -6 + rand() * 12;

  return (
    <Layer>
      <div style={{ position: 'absolute', inset: 0, clipPath: 'inset(9%)' }}>
        <Patch
          mask={PATTERN.hatch(1, true)}
          scale={spacing}
          color={COLOR_VAR.accentSoft}
          opacity={visualOpacity(opacity * 0.5)}
          rotate={skew}
          style={{ inset: '-25%' }}
        />
      </div>
      {Array.from({ length: count }, (_, i) => (
        // Solid hairlines, full height. v1 faded each one top and bottom with
        // a linear gradient; a rule that stops is a rule that was drawn short.
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${rand() * 100}%`,
            insetBlock: 0,
            inlineSize: '1px',
            backgroundColor: COLOR_VAR.accent,
            opacity: visualOpacity(opacity * 0.45),
            mixBlendMode: VISUAL_BLEND,
          }}
        />
      ))}
    </Layer>
  );
}

// --- particle-field (kept) --------------------------------------------------

/** Scattered points. Audited rather than rewritten: dots were already dots,
 * and the only change is that the `filter: blur(0.5px)` softening each one is
 * gone. Half a pixel of blur is not a bloom by eye, but rule 19 bans the
 * property rather than the radius on purpose — "a little blur" is how the
 * effect returns, and a check that has to judge how much is not a check. */
export function ParticleField({ props }: { props: AbstractVisualProps }) {
  const rand = mulberry32(props.seed);
  const { count, opacity } = INTENSITY[props.intensity];
  const particles = Array.from({ length: count * 18 }, (_, i) => ({
    left: rand() * 100,
    top: rand() * 100,
    size: 1 + rand() * 3,
    dim: 0.2 + rand() * 0.8,
    color: roleAt(i),
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
            backgroundColor: p.color,
            opacity: visualOpacity(opacity * p.dim),
            mixBlendMode: VISUAL_BLEND,
          }}
        />
      ))}
    </Layer>
  );
}

// --- block-collage (new) ----------------------------------------------------

/** Hard-edged colour blocks, riso-offset. The sixth generator, and the one
 * that exists to prove the vocabulary gained range rather than merely losing
 * gradients: every other generator is a field of small marks, and this one is
 * composition at scale.
 *
 * Each block is drawn twice — once in one token colour, once in another,
 * nudged by a few pixels. That is misregistration, and it is the whole effect;
 * there is no third mechanism and no blur anywhere in it. */
export function BlockCollage({ props }: { props: AbstractVisualProps }) {
  const rand = mulberry32(props.seed);
  const { count, opacity } = INTENSITY[props.intensity];
  const blocks = Array.from({ length: count + 1 }, (_, i) => ({
    left: rand() * 70,
    top: rand() * 65,
    width: 18 + rand() * 40,
    height: 12 + rand() * 38,
    offset: 3 + rand() * 6,
    angle: -3 + rand() * 6,
    color: roleAt(i),
    shadow: roleAt(i + 1),
  }));

  return (
    <Layer>
      {blocks.flatMap((b, i) =>
        // The misregistered plate first, so the main one sits over it.
        [
          { key: `${i}-off`, color: b.shadow, dx: b.offset, dy: b.offset, o: 0.7 },
          { key: `${i}`, color: b.color, dx: 0, dy: 0, o: 1 },
        ].map((plate) => (
          <div
            key={plate.key}
            style={{
              position: 'absolute',
              left: `${b.left}%`,
              top: `${b.top}%`,
              inlineSize: `${b.width}%`,
              blockSize: `${b.height}%`,
              backgroundColor: plate.color,
              translate: `${plate.dx}px ${plate.dy}px`,
              rotate: `${b.angle.toFixed(2)}deg`,
              opacity: visualOpacity(opacity * 0.55 * plate.o),
              mixBlendMode: VISUAL_BLEND,
            }}
          />
        )),
      )}
    </Layer>
  );
}

export type { Intensity };
