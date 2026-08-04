// The shared piece every layout needed — six near-identical stack-with-
// stagger helpers would have been the duplication this phase's Search
// section warns about. One region's blocks, staggered and revealed.

import type { CSSProperties } from 'react';

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import { staggerDelayMs } from '@/features/art-direction';
import type { Block } from '@/schema';

import { BlockRenderer } from '../blocks';
import { Reveal } from '../motion/reveal';
import { spaceVar } from '../tokens';

export function RegionBlocks({
  blocks,
  artDirection,
  motion,
  style,
}: {
  blocks: Block[] | undefined;
  artDirection: ArtDirection;
  motion: MotionVocabulary;
  style?: CSSProperties;
}) {
  if (!blocks || blocks.length === 0) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: spaceVar(4), ...style }}>
      {blocks.map((block, i) => (
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
