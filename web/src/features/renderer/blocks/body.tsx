import type { ArtDirection } from '@/features/art-direction';

import type { BodyProps } from './block-props';
import { MEASURE, typeStyle } from '../tokens';

export function BodyBlock({
  props,
  artDirection,
}: {
  props: BodyProps;
  artDirection: ArtDirection;
}) {
  const role = props.emphasis ?? 'normal';
  return (
    <p style={{ ...typeStyle(role, artDirection), maxInlineSize: MEASURE }}>
      {props.text}
    </p>
  );
}
