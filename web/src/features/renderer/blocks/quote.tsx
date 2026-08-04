import type { ArtDirection } from '@/features/art-direction';

import type { QuoteProps } from './block-props';
import { MEASURE, spaceVar, typeStyle } from '../tokens';

export function QuoteBlock({
  props,
  artDirection,
}: {
  props: QuoteProps;
  artDirection: ArtDirection;
}) {
  const attribution = props.attribution;
  const role = props.role;
  return (
    <blockquote
      style={{ margin: 0, maxInlineSize: MEASURE, paddingInlineStart: spaceVar(4) }}
    >
      <p style={typeStyle('lead', artDirection)}>{props.text}</p>
      {attribution ? (
        <footer
          style={{ ...typeStyle('muted', artDirection), marginBlockStart: spaceVar(3) }}
        >
          {attribution}
          {role ? `, ${role}` : ''}
        </footer>
      ) : null}
    </blockquote>
  );
}
