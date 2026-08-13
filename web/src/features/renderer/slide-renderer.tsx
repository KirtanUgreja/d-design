/**
 * Slide renderer — one slide's markup, framed by its layout archetype.
 *
 * The archetype determines the frame (how blocks are arranged); the design
 * family's CSS custom properties determine the look. The model picked the
 * archetype by id; the renderer owns the arrangement.
 */

import type { Slide } from '../../schema/generated/Deck.js';
import type { MotionVocabulary } from '../design-system/index.js';
import { BlockView } from './blocks.js';

export type SlideRendererProps = {
  slide: Slide;
  motion: MotionVocabulary;
  images?: Record<string, string>;
};

export function SlideRenderer({ slide, motion, images }: SlideRendererProps) {
  const className = `dds-slide dds-slide--${slide.layout_archetype}${
    slide.variant ? ` dds-slide--${slide.variant}` : ''
  }`;
  const src = images?.[slide.id];

  return (
    <section className={className} aria-label={slide.title} data-archetype={slide.layout_archetype}>
      <div className="dds-slide__inner">
        {slide.blocks.map((block, i) => (
          <BlockView key={`${block.kind}-${i}`} block={block} motion={motion} src={src} />
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
