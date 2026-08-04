import type { ArtDirection } from '@/features/art-direction';

import { placeholderImageSrc } from './asset-placeholder';
import type { ImageProps } from './block-props';
import { spaceVar } from '../tokens';

export function ImageBlock({
  props,
  artDirection,
}: {
  props: ImageProps;
  artDirection: ArtDirection;
}) {
  const framed = props.treatment === 'framed';
  return (
    <img
      src={placeholderImageSrc(artDirection)}
      alt={props.alt}
      loading="lazy"
      style={{
        display: 'block',
        inlineSize: '100%',
        blockSize: props.treatment === 'bleed' ? '100%' : 'auto',
        objectFit: props.fit,
        ...(framed ? { padding: spaceVar(2), border: '1px solid var(--hairline)' } : {}),
      }}
    />
  );
}
