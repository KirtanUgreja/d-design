import type { ArtDirection } from '@/features/art-direction';

import type { ListProps } from './block-props';
import { CheckIcon } from './icons';
import { COLOR_VAR, MEASURE, spaceVar, typeStyle } from '../tokens';

export function ListBlock({
  props,
  artDirection,
}: {
  props: ListProps;
  artDirection: ArtDirection;
}) {
  return (
    <ul
      style={{
        listStyle: 'none',
        margin: 0,
        padding: 0,
        maxInlineSize: MEASURE,
        display: 'flex',
        flexDirection: 'column',
        gap: spaceVar(3),
      }}
    >
      {props.items.map((item, i) => (
        // Index, not text: `ListItem` has no id and the schema allows
        // duplicate text across items (list.style validation doesn't
        // dedupe) — hostile.json's numbered fixture has five identical
        // items on purpose, to check exactly this.
        <li
          key={i}
          style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: spaceVar(2),
          }}
        >
          <Marker style={props.style} index={i} artDirection={artDirection} />
          <span>
            <span style={typeStyle('normal', artDirection)}>{item.text}</span>
            {item.detail ? (
              <span style={{ ...typeStyle('muted', artDirection), display: 'block' }}>
                {item.detail}
              </span>
            ) : null}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Marker({
  style,
  index,
  artDirection,
}: {
  style: ListProps['style'];
  index: number;
  artDirection: ArtDirection;
}) {
  if (style === 'checks') return <CheckIcon color={COLOR_VAR.accent} />;
  if (style === 'numbered') {
    return (
      <span style={{ ...typeStyle('normal', artDirection), color: COLOR_VAR.accent }}>
        {index + 1}.
      </span>
    );
  }
  return (
    <span aria-hidden="true" style={{ color: COLOR_VAR.accent }}>
      •
    </span>
  );
}
