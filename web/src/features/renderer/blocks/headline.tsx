import type { ArtDirection } from '@/features/art-direction';

import type { HeadlineProps } from './block-props';
import { typeStyle } from '../tokens';

export function HeadlineBlock({
  props,
  artDirection,
}: {
  props: HeadlineProps;
  artDirection: ArtDirection;
}) {
  const role = props.emphasis ?? 'section';
  return <h2 style={typeStyle(role, artDirection)}>{props.text}</h2>;
}
