import type { ArtDirection } from '@/features/art-direction';

import type { AbstractVisualProps } from './block-props';
import { GradientMesh } from './gradient-mesh';
import { GridLines, NoiseVeil, Orb, ParticleField } from './visuals';

// All five generators, as of phase 11 (docs/v1/plan/11-visuals-and-slot.md).
// A switch rather than a lookup table because each component's props type is
// checked at the call site this way, and there are five of them, forever —
// "a sixth generator" is in that phase's Skipped list with a trigger.
export function AbstractVisualBlock({
  props,
  artDirection,
}: {
  props: AbstractVisualProps;
  artDirection: ArtDirection;
}) {
  const palette = artDirection.color;
  switch (props.generator) {
    case 'gradient-mesh':
      return <GradientMesh props={props} palette={palette} />;
    case 'particle-field':
      return <ParticleField props={props} palette={palette} />;
    case 'grid-lines':
      return <GridLines props={props} palette={palette} />;
    case 'orb':
      return <Orb props={props} palette={palette} />;
    case 'noise-veil':
      return <NoiseVeil props={props} palette={palette} />;
  }
}
