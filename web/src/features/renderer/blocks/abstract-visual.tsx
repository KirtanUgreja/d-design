import type { AbstractVisualProps } from './block-props';
import {
  BlockCollage,
  DitherFade,
  GridLines,
  HalftoneField,
  HatchDrift,
  ParticleField,
} from './visuals';

// All six generators, as of v2 phase 14 (docs/v2/plan/14-texture-without-gradient.md).
// A switch rather than a lookup table because each component's props type is
// checked at the call site this way.
//
// The trigger v1 set for a sixth generator was "a real need"; the need was
// that five generators all rendered fields of small marks and none of them
// composed at scale, which is what `block-collage` is for.
//
// No `artDirection` parameter any more. The generators used to take a palette
// so they could call `toCssColor` on it; they read `COLOR_VAR` now, so colour
// stays a token reference and this component has nothing to forward.
export function AbstractVisualBlock({ props }: { props: AbstractVisualProps }) {
  switch (props.generator) {
    case 'halftone-field':
      return <HalftoneField props={props} />;
    case 'particle-field':
      return <ParticleField props={props} />;
    case 'grid-lines':
      return <GridLines props={props} />;
    case 'hatch-drift':
      return <HatchDrift props={props} />;
    case 'dither-fade':
      return <DitherFade props={props} />;
    case 'block-collage':
      return <BlockCollage props={props} />;
  }
}
