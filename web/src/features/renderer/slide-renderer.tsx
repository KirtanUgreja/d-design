/**
 * Slide renderer — one slide's markup, driven by its generated layout.
 *
 * The slide's layout is a sequence of regions (role + span + emphasis), and
 * the design family's CSS custom properties determine the look. The model
 * *generated* the layout within the family's grammar (phase 10); the renderer
 * owns the arrangement — it maps regions to grid cells and allocates blocks to
 * the region whose role they fill. The renderer knows no catalogue and no
 * archetype: it renders any grammar-legal layout the schema carries.
 */

import type { LayoutRegion, Slide } from '../../schema/generated/Deck.js';
import type { MotionVocabulary } from '../design-system/index.js';
import { BlockView } from './blocks.js';

export type SlideRendererProps = {
  slide: Slide;
  motion: MotionVocabulary;
  images?: Record<string, string>;
};

/** The role a block fills — must match api/schema/deck.py `_block_fills_role`. */
function blockFillsRole(block: Slide['blocks'][number], role: string): boolean {
  if (block.kind === 'text') {
    if (block.style === 'headline') return role === 'headline';
    if (block.style === 'eyebrow' || block.style === 'caption') return role === 'aside';
    return role === 'body';
  }
  if (block.kind === 'stat') return role === 'stats';
  if (block.kind === 'quote') return role === 'quote';
  if (block.kind === 'chart') return role === 'chart';
  if (block.kind === 'image') return role === 'media';
  return false;
}

function blocksForRegion(slide: Slide, region: LayoutRegion): Slide['blocks'] {
  return slide.blocks.filter((b) => blockFillsRole(b, region.role));
}

export function SlideRenderer({ slide, motion, images }: SlideRendererProps) {
  const src = images?.[slide.id];

  return (
    <section className="dds-slide" aria-label={slide.title}>
      <div className="dds-slide__inner">
        {slide.layout.regions.map((region, i) => (
          <div
            key={`${region.role}-${i}`}
            className="dds-region"
            data-role={region.role}
            data-span={region.span}
            data-emphasis={region.emphasis}
          >
            {blocksForRegion(slide, region).map((block, j) => (
              <BlockView key={`${block.kind}-${j}`} block={block} motion={motion} src={src} />
            ))}
          </div>
        ))}
        {slide.cta && (
          <a className="dds-cta" href={slide.cta.destination}>
            {slide.cta.label}
          </a>
        )}
      </div>
    </section>
  );
}
