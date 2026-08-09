// One texture layer, rendered. The art direction's `texture` list is the
// structure — which kinds, in what order, how many bands — and every *value*
// (opacity, colour, tile size, angle, offset) is read back out of a custom
// property that `to-css-vars.ts` emitted. Nothing here turns a token into a
// string. docs/v2/plan/14-texture-without-gradient.md.
//
// The pattern is always a colourless mask and the colour is always a token
// underneath it, which is what makes the no-gradient rule structural rather
// than a habit: there is no ramp available in this file to reach for.

import type { CSSProperties } from 'react';

import type { Density, TextureLayer } from '@/features/art-direction';

import * as PATTERN from './patterns';
import { textureVar } from '../tokens';

/** Masked paint, sized and rotated. The rotation is applied to an oversized
 * element rather than to the tile: a square tile repeated at an arbitrary
 * angle shows seams along the tile grid, and an element inset past the frame
 * on every side has no visible edge to seam against. */
function Masked({
  index,
  mask,
  rotate,
  clip,
  opacity,
}: {
  index: number;
  mask: string;
  rotate?: boolean;
  clip?: string;
  /** A fixed multiplier for a band, *not* a token. Bands differ by density of
   * mark, not by fading — this only keeps a sparse outer band from reading
   * heavier than the dense inner one at the same coverage. */
  opacity?: number;
}) {
  const transforms = [
    `translate(${textureVar(index, 'offset')}, ${textureVar(index, 'offset')})`,
    ...(rotate === true ? [`rotate(${textureVar(index, 'angle')})`] : []),
  ];
  const style: CSSProperties = {
    position: 'absolute',
    // Past the frame on every side, so a rotated tile grid never shows its
    // corner inside the scene.
    inset: '-40%',
    transform: transforms.join(' '),
    backgroundColor: textureVar(index, 'color'),
    maskImage: mask,
    WebkitMaskImage: mask,
    maskRepeat: 'repeat',
    WebkitMaskRepeat: 'repeat',
    maskSize: `${textureVar(index, 'scale')} ${textureVar(index, 'scale')}`,
    WebkitMaskSize: `${textureVar(index, 'scale')} ${textureVar(index, 'scale')}`,
    opacity:
      opacity === undefined
        ? textureVar(index, 'opacity')
        : `calc(${textureVar(index, 'opacity')} * ${opacity})`,
    ...(clip === undefined ? {} : { clipPath: clip }),
  };
  return <div style={style} />;
}

/** Bands run 1..steps. Density is the *only* thing that changes between them,
 * and it changes in whole units — which is the difference between a halftone
 * and a gradient someone quantised. */
const bandDensities = (steps: number): Density[] =>
  Array.from(
    { length: steps },
    (_, i) => (4 - Math.round((i * 3) / (steps - 1))) as Density,
  );

/** A dot bloom in hard-edged concentric bands, anchored where a light source
 * would be. Replaces the radial-gradient glow.
 *
 * Painted largest first so the densest band lands on top. That ordering is
 * load-bearing: a mask's coverage is the *union* of what is stacked, so bands
 * only read as separate when the denser one is drawn over the sparser. */
function HalftoneBloom({ index, steps }: { index: number; steps: number }) {
  const densities = bandDensities(steps);
  return (
    <>
      {densities
        .map((density, band) => ({
          density,
          // Widest ring outermost; the innermost band is the light source.
          radius: 100 - (band * 70) / steps,
        }))
        .reverse()
        .map(({ density, radius }) => (
          <Masked
            key={radius}
            index={index}
            mask={PATTERN.halftone(density)}
            rotate
            clip={`ellipse(${radius}% ${radius * 0.8}% at 50% 0%)`}
          />
        ))}
    </>
  );
}

/** A Bayer dissolve inward from the frame edge, in hard bands. Replaces the
 * radial-gradient vignette.
 *
 * Each band is a **ring**, drawn as four strips, and that is not a stylistic
 * choice — Bayer levels nest, so every cell lit at level 4 is lit at level 9.
 * Stacking nested levels yields the densest one everywhere, which is a flat
 * field. Non-overlapping regions are the only way the dissolve is a dissolve.
 * Four strips beat a `polygon(evenodd)` hole because they are four divs that
 * cannot be wrong. */
function DitherVignette({ index, steps }: { index: number; steps: number }) {
  const densities = bandDensities(steps);
  return (
    <>
      {densities.map((density, band) => {
        const outer = (band * 22) / steps;
        const inner = ((band + 1) * 22) / steps;
        const mask = PATTERN.dither(PATTERN.DITHER_LEVEL[density]);
        // The ring between `outer` and `inner`, as top / bottom / left / right.
        const strips: string[] = [
          `inset(${outer}% ${outer}% ${100 - inner}% ${outer}%)`,
          `inset(${100 - inner}% ${outer}% ${outer}% ${outer}%)`,
          `inset(${inner}% ${100 - inner}% ${inner}% ${outer}%)`,
          `inset(${inner}% ${outer}% ${inner}% ${100 - inner}%)`,
        ];
        return strips.map((clip, i) => (
          <Masked key={`${band}-${i}`} index={index} mask={mask} clip={clip} />
        ));
      })}
    </>
  );
}

export function TextureLayerView({
  layer,
  index,
}: {
  layer: TextureLayer;
  index: number;
}) {
  switch (layer.kind) {
    case 'grain':
      return <Masked index={index} mask={PATTERN.grain(layer.density)} />;
    case 'weave':
      return <Masked index={index} mask={PATTERN.weave(layer.density)} />;
    case 'hatch':
      return (
        <Masked index={index} mask={PATTERN.hatch(layer.density, layer.cross)} rotate />
      );
    case 'rule':
      return <Masked index={index} mask={PATTERN.rule(layer.axis, layer.weight)} />;
    case 'halftone':
      return <HalftoneBloom index={index} steps={layer.steps} />;
    case 'dither':
      return <DitherVignette index={index} steps={layer.steps} />;
  }
}
