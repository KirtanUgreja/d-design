/**
 * DeckRenderer — the pure renderer core (patterns.md rule 2).
 *
 * A pure function of (deck, designFamily, motion): no knowledge of editor,
 * export, or present. No `mode` prop, no process.env, no typeof window —
 * behavior is injected from outside by the wrappers (export in phase 05).
 *
 * The exported deck is a single self-contained HTML file; progressive
 * enhancement is the floor (frontend.md): the markup is complete and readable
 * without JS. Reveals animate in from a visible resting state, never out of
 * opacity: 0.
 */

import type { Deck } from '../../schema/generated/Deck.js';
import { familyTokens } from '../design-system/index.js';
import type { MotionVocabulary } from '../design-system/index.js';
import { SlideRenderer } from './slide-renderer.js';

export type DeckRendererProps = {
  deck: Deck;
  motion: MotionVocabulary;
  images?: Record<string, string>;
};

export function DeckRenderer({ deck, motion, images }: DeckRendererProps) {
  const spec = familyTokens(deck.family_id);
  if (!spec) {
    // An unknown family is a pipeline bug, not a render choice: the family
    // registry is the single source of visual truth, and a deck that names a
    // family without tokens must not silently render unstyled.
    throw new Error(`unknown design family: ${deck.family_id}`);
  }

  return (
    <div
      className="dds-deck"
      style={{ '--dds-family': deck.family_id } as React.CSSProperties}
      data-family={deck.family_id}
    >
      {deck.slides.map((slide) => (
        <SlideRenderer key={slide.id} slide={slide} motion={motion} images={images} />
      ))}
    </div>
  );
}
