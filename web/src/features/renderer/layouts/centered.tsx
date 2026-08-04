import type { LayoutProps } from './region';
import { RegionBlocks } from './region-blocks';
import { MEASURE, spaceVar } from '../tokens';

export function CenteredLayout({ blocksByRegion, artDirection, motion }: LayoutProps) {
  return (
    <div
      style={{
        maxInlineSize: MEASURE,
        marginInline: 'auto',
        textAlign: 'center',
      }}
    >
      <RegionBlocks
        blocks={blocksByRegion.content}
        artDirection={artDirection}
        motion={motion}
        style={{ alignItems: 'center', gap: spaceVar(5) }}
      />
    </div>
  );
}
