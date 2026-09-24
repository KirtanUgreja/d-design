/**
 * The editor canvas — wraps the pure renderer (patterns.md rule 2).
 *
 * The renderer core is untouched: no `mode` prop, no selection knowledge.
 * Selection is an overlay the canvas draws around the rendered output — a
 * clickable shell per slide with a hairline and a label (app.md: "selection
 * is a hairline and a label", not a saturated box). What you edit here is
 * byte-for-byte what the exporter produces for the same (deck, family).
 */
'use client';

import type { Deck } from '../../schema/generated/Deck.js';
import { familyTokens } from '../design-system/index.js';
import { DeckRenderer } from '../renderer/index.js';

export type EditorCanvasProps = {
  deck: Deck;
  /** Image data URIs, keyed by slide id — passed straight to the pure renderer
   * so the canvas shows the same images the export will inline. */
  images: Record<string, string>;
  selection: string | null;
  onSelect: (id: string | null) => void;
};

export function EditorCanvas({ deck, images, selection, onSelect }: EditorCanvasProps) {
  const motion = familyTokens(deck.family_id)?.motion ?? { reveal: 'rise', pacing: 'steady' };

  return (
    <div className="editor-canvas" data-editor-canvas>
      {deck.slides.map((slide) => {
        const selected = slide.id === selection;
        return (
          <div
            key={slide.id}
            className={`editor-slide${selected ? ' editor-slide--selected' : ''}`}
            data-editor-slide={slide.id}
            data-selected={selected || undefined}
            onClick={(e) => {
              // Stop the click from bubbling to the canvas (deselect) when a
              // slide shell is clicked — clicking the empty canvas deselects.
              e.stopPropagation();
              onSelect(selected ? null : slide.id);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') onSelect(null);
            }}
          >
            {selected && <span className="editor-slide__label">{slide.title}</span>}
            <DeckRenderer deck={{ ...deck, slides: [slide] }} motion={motion} images={images} />
          </div>
        );
      })}
    </div>
  );
}
