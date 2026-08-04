import type { LayoutProps } from './region';
import { RegionBlocks } from './region-blocks';
import { CONTENT_MAX, spaceVar } from '../tokens';

export function StackLayout({ blocksByRegion, artDirection, motion }: LayoutProps) {
  return (
    <div
      style={{
        maxInlineSize: CONTENT_MAX,
        marginInline: 'auto',
      }}
    >
      <RegionBlocks
        blocks={blocksByRegion.content}
        artDirection={artDirection}
        motion={motion}
        style={{ gap: spaceVar(6) }}
      />
    </div>
  );
}
