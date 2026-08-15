/**
 * A sample deck — the editor's starting document (app.md: "one sample artifact
 * in the account"). Mirrors the golden fixture in api/tests/fixtures.py so the
 * editor opens with real, schema-valid work that round-trips through the
 * renderer and the exporter.
 */
import type { Deck } from '../../schema/generated/Deck.js';

export const SAMPLE_DECK: Deck = {
  family_id: 'editorial-serif',
  slides: [
    {
      id: 's1',
      title: 'The quiet power of editorial design',
      layout: {
        regions: [
          { role: 'headline', span: 'full', emphasis: 'primary' },
          { role: 'body', span: 'full' },
        ],
      },
      blocks: [
        { kind: 'text', style: 'headline', content: 'The quiet power of editorial design' },
        {
          kind: 'text',
          style: 'body',
          content: 'How restraint, typography, and rhythm make a brand unforgettable.',
        },
      ],
      cta: { label: 'Read the essay', destination: 'https://example.com/essay' },
      motion_intent: 'reveal',
    },
    {
      id: 's2',
      title: 'Three ways to be remembered',
      layout: {
        regions: [
          { role: 'headline', span: 'full' },
          { role: 'body', span: 'full' },
          { role: 'quote', span: 'full' },
        ],
      },
      blocks: [
        { kind: 'text', style: 'headline', content: 'Three ways to be remembered' },
        {
          kind: 'text',
          style: 'body',
          content: 'Restraint, typography, and rhythm each leave a mark.',
        },
        {
          kind: 'quote',
          text: 'Design is not just how it looks — it is how it works.',
          attribution: 'Steve Jobs',
        },
      ],
      motion_intent: 'reveal',
    },
    {
      id: 's3',
      title: 'What the reader takes away',
      layout: {
        regions: [
          { role: 'headline', span: 'full' },
          { role: 'quote', span: 'full' },
        ],
      },
      blocks: [
        { kind: 'text', style: 'headline', content: 'What the reader takes away' },
        {
          kind: 'quote',
          text: 'A single idea, held up by evidence, is what survives.',
          attribution: 'The author',
        },
      ],
      motion_intent: 'emphasize',
    },
  ],
};
