import type { ArtDirection } from '@/features/art-direction';

import type { AbstractVisualProps } from './block-props';
import { GradientMesh } from './gradient-mesh';

export function AbstractVisualBlock({
  props,
  artDirection,
}: {
  props: AbstractVisualProps;
  artDirection: ArtDirection;
}) {
  // ponytail: only gradient-mesh is implemented this phase (docs/v1/plan/04-
  // renderer.md — the other four are phase 11, tuned against real generated
  // content). The schema already allows all five, so the other four fall
  // back to gradient-mesh rather than rendering nothing.
  return <GradientMesh props={props} palette={artDirection.color} />;
}
