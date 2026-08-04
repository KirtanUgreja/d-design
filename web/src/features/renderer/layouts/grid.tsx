import { staggerDelayMs } from '@/features/art-direction';

import { BlockRenderer } from '../blocks';
import { Reveal } from '../motion/reveal';
import type { LayoutProps } from './region';
import { CONTENT_MAX, spaceVar } from '../tokens';

// 2-4 blocks, one per cell (docs/v1/scene-schema.md: "grid layout: 2-4 blocks
// in cells"), so each block IS a grid item — unlike every other layout,
// there is no per-region vertical stack to delegate to RegionBlocks here.
export function GridLayout({ blocksByRegion, artDirection, motion }: LayoutProps) {
  const cells = blocksByRegion.cells ?? [];
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${Math.min(Math.max(cells.length, 1), 4)}, 1fr)`,
        gap: spaceVar(6),
        maxInlineSize: CONTENT_MAX,
        marginInline: 'auto',
      }}
    >
      {cells.map((block, i) => (
        <Reveal
          key={block.id}
          intent={block.motion ?? 'reveal'}
          vocabulary={motion}
          delayMs={staggerDelayMs(motion, i)}
        >
          <BlockRenderer block={block} artDirection={artDirection} motion={motion} />
        </Reveal>
      ))}
    </div>
  );
}
