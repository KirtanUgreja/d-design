import type { LayoutProps } from './region';
import { RegionBlocks } from './region-blocks';
import { CONTENT_MAX, spaceVar } from '../tokens';

// `left`/`right` name authoring position, not screen position. DOM order —
// `left` region first — is what a browser mirrors under `dir="rtl"" with no
// stylesheet change (docs/v1/scene-schema.md).
export function SplitLeftLayout({ blocksByRegion, artDirection, motion }: LayoutProps) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: spaceVar(6),
        alignItems: 'center',
        maxInlineSize: CONTENT_MAX,
        marginInline: 'auto',
      }}
    >
      <RegionBlocks
        blocks={blocksByRegion.left}
        artDirection={artDirection}
        motion={motion}
      />
      <RegionBlocks
        blocks={blocksByRegion.right}
        artDirection={artDirection}
        motion={motion}
      />
    </div>
  );
}
