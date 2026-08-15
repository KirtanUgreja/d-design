/**
 * The property panel — generated from the schema's shape (phase 12).
 *
 * app.md: the panel is generated from a schema with no presentational fields,
 * so there is no colour picker and no font size — those are unrepresentable.
 * What can be edited: copy (the blocks), emphasis (the layout region's
 * hierarchy — the replacement vocabulary for a font-size field), and slide
 * order. A designed note shows where the colour picker would be: the family
 * owns the look.
 */
'use client';

import { DESIGN_FAMILY_TOKENS } from '../design-system/index.js';
import type { Deck, Slide } from '../../schema/generated/Deck.js';

export type PropertyPanelProps = {
  deck: Deck;
  slide: Slide;
  slideIndex: number;
  slideCount: number;
  onPatchBlock: (blockIndex: number, content: string) => void;
  onPatchRegion: (regionIndex: number, emphasis: (typeof EMPHASIS)[number]) => void;
  onReorder: (from: number, to: number) => void;
};

const EMPHASIS = ['primary', 'secondary', 'quiet'] as const;

export function PropertyPanel({
  deck,
  slide,
  slideIndex,
  slideCount,
  onPatchBlock,
  onPatchRegion,
  onReorder,
}: PropertyPanelProps) {
  const familyName = DESIGN_FAMILY_TOKENS[deck.family_id]?.tokens.id ?? deck.family_id;

  return (
    <div className="editor-panel" data-editor-panel>
      <h2 className="editor-panel__title">Slide {slideIndex + 1}</h2>

      <section className="editor-panel__group">
        <h3>Copy</h3>
        {slide.blocks.map((block, i) => {
          if (block.kind !== 'text' || (block.style !== 'headline' && block.style !== 'body')) {
            return null;
          }
          return (
            <label key={`${block.style}-${i}`} className="editor-panel__field">
              <span>{block.style === 'headline' ? 'Headline' : 'Body'}</span>
              <textarea
                value={block.content}
                rows={block.style === 'headline' ? 2 : 3}
                onChange={(e) => onPatchBlock(i, e.target.value)}
              />
            </label>
          );
        })}
      </section>

      <section className="editor-panel__group">
        <h3>Emphasis</h3>
        {slide.layout.regions.map((region, i) => (
          <label key={`${region.role}-${i}`} className="editor-panel__field">
            <span>{region.role} region</span>
            <select
              value={region.emphasis ?? 'secondary'}
              onChange={(e) => {
                const v = e.target.value as (typeof EMPHASIS)[number];
                onPatchRegion(i, v);
              }}
            >
              {EMPHASIS.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </label>
        ))}
      </section>

      <section className="editor-panel__group">
        <h3>Order</h3>
        <div className="editor-panel__row">
          <button onClick={() => onReorder(slideIndex, slideIndex - 1)} disabled={slideIndex === 0}>
            ↑ Move up
          </button>
          <button
            onClick={() => onReorder(slideIndex, slideIndex + 1)}
            disabled={slideIndex === slideCount - 1}
          >
            ↓ Move down
          </button>
        </div>
      </section>

      <p className="editor-panel__note">
        Type, colour and spacing come from the <strong>{familyName}</strong> design family, so this
        cannot go off-brand. Change the family, not the pixel.
      </p>
    </div>
  );
}
