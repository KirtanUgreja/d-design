import type { LayoutProps } from './region';
import { RegionBlocks } from './region-blocks';
import { CONTENT_MAX, SCENE_PADDING_INLINE } from '../tokens';

export function FullBleedLayout({ blocksByRegion, artDirection, motion }: LayoutProps) {
  return (
    <div
      style={{
        position: 'relative',
        minBlockSize: '100vh',
        display: 'grid',
        placeItems: 'center',
      }}
    >
      <div style={{ position: 'absolute', inset: 0 }}>
        <RegionBlocks
          blocks={blocksByRegion.bg}
          artDirection={artDirection}
          motion={motion}
        />
      </div>
      <div
        style={{
          position: 'relative',
          zIndex: 1,
          maxInlineSize: CONTENT_MAX,
          paddingInline: SCENE_PADDING_INLINE,
          textAlign: 'center',
        }}
      >
        <RegionBlocks
          blocks={blocksByRegion.content}
          artDirection={artDirection}
          motion={motion}
          style={{ alignItems: 'center' }}
        />
      </div>
    </div>
  );
}
