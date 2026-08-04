// Region resolution — one place, shared by every layout, per
// docs/v1/scene-schema.md -> "Default region: content, or cells for grid, or
// left for splits."

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import type { Block, Scene } from '@/schema';

export type Layout = Scene['layout'];
export type Region = NonNullable<Block['region']>;

const DEFAULT_REGION: Record<Layout, Region> = {
  'full-bleed': 'content',
  'split-left': 'left',
  'split-right': 'left',
  centered: 'content',
  stack: 'content',
  grid: 'cells',
};

export function resolveRegion(block: Block, layout: Layout): Region {
  return block.region ?? DEFAULT_REGION[layout];
}

export function groupByRegion(
  blocks: readonly Block[],
  layout: Layout,
): Partial<Record<Region, Block[]>> {
  const groups: Partial<Record<Region, Block[]>> = {};
  for (const block of blocks) {
    const region = resolveRegion(block, layout);
    (groups[region] ??= []).push(block);
  }
  return groups;
}

export interface LayoutProps {
  blocksByRegion: Partial<Record<Region, Block[]>>;
  artDirection: ArtDirection;
  motion: MotionVocabulary;
}
