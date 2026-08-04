import type { ArtDirection } from '@/features/art-direction';

import type { CtaProps } from './block-props';
import { isSafeHref } from './href-safety';
import { COLOR_VAR, spaceVar, typeStyle } from '../tokens';

export function CtaBlock({
  props,
  artDirection,
}: {
  props: CtaProps;
  artDirection: ArtDirection;
}) {
  const primary = props.style === 'primary';
  const style = {
    ...typeStyle('normal', artDirection),
    display: 'inline-block',
    paddingBlock: spaceVar(2),
    paddingInline: spaceVar(4),
    borderRadius: spaceVar(1),
    textDecoration: 'none',
    ...(primary
      ? { background: COLOR_VAR.accent, color: COLOR_VAR.bg }
      : {
          background: 'transparent',
          color: COLOR_VAR.ink,
          border: `1px solid ${COLOR_VAR.hairline}`,
        }),
  };

  // Fail closed (patterns.md rule 5): an href that fails the render-time
  // allowlist renders as inert text, never as a clickable link.
  if (!isSafeHref(props.href)) {
    return <span style={style}>{props.label}</span>;
  }

  return (
    <a href={props.href} style={style}>
      {props.label}
    </a>
  );
}
