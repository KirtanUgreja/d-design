import type { LayoutProps } from './region';
import { RegionBlocks } from './region-blocks';
import { CONTENT_MAX, spaceVar } from '../tokens';

// Same two named regions as split-left, DOM order reversed — `right` is
// authored first so it lands on the visual-start side ("visual left,
// content right" in the layout table), and still mirrors correctly under
// RTL because it's DOM order driving it, not a physical left/right rule.
export function SplitRightLayout({ blocksByRegion, artDirection, motion }: LayoutProps) {
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
        blocks={blocksByRegion.right}
        artDirection={artDirection}
        motion={motion}
      />
      <RegionBlocks
        blocks={blocksByRegion.left}
        artDirection={artDirection}
        motion={motion}
      />
    </div>
  );
}
