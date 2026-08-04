import type { ArtDirection } from '@/features/art-direction';

import type { EyebrowProps } from './block-props';
import { typeStyle } from '../tokens';

export function EyebrowBlock({
  props,
  artDirection,
}: {
  props: EyebrowProps;
  artDirection: ArtDirection;
}) {
  return <p style={typeStyle('eyebrow', artDirection)}>{props.text}</p>;
}
