import type { ArtDirection } from '@/features/art-direction';

import { placeholderImageSrc } from './asset-placeholder';
import type { VideoProps } from './block-props';

// ponytail: no `src` until storage.ts (phase 10) resolves `assetId` to a
// playable URL. The poster placeholder is real; the element itself has
// nothing to play yet, which is honest rather than pointing at a fake file.

export function VideoBlock({
  props,
  artDirection,
}: {
  props: VideoProps;
  artDirection: ArtDirection;
}) {
  // An autoplaying video with sound on someone's launch page is a defect —
  // autoplay implies muted and playsInline, always, regardless of the prop.
  const autoplay = props.autoplay;
  return (
    <video
      autoPlay={autoplay}
      muted={autoplay}
      playsInline={autoplay}
      loop={props.loop}
      controls={!autoplay}
      poster={placeholderImageSrc(artDirection)}
      style={{ display: 'block', inlineSize: '100%', blockSize: 'auto' }}
    />
  );
}
