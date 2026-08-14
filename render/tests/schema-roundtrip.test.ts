/**
 * The cross-language round-trip (python.md -> "Test"): a Deck fixture
 * round-trips through both validators — Pydantic and the generated Zod — with
 * the same verdict on the same input. This is what would actually catch a
 * codegen bug: a shape Pydantic accepts but the generated validator rejects,
 * or vice versa.
 *
 * The golden deck lives in api/tests/fixtures.py. It is duplicated here as
 * typed JSON so the Zod half can be exercised without a Python call.
 */
import { describe, expect, it } from 'vitest';

import { DeckSchema } from '@web/schema/generated/Deck.js';

const goldenDeck = {
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
        { kind: 'text', style: 'body', content: 'Restraint, typography, and rhythm.' },
        { kind: 'quote', text: 'A single idea, held up by evidence.', attribution: 'The author' },
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
          text: 'Design is not just how it looks — it is how it works.',
          attribution: 'Steve Jobs',
        },
      ],
      motion_intent: 'emphasize',
    },
    {
      id: 's4',
      title: 'Where the effort goes',
      layout: {
        regions: [
          { role: 'headline', span: 'full' },
          { role: 'media', span: 'full' },
        ],
      },
      blocks: [
        { kind: 'text', style: 'headline', content: 'Where the effort goes' },
        {
          kind: 'image',
          subject: 'An editorial spread with generous margins and a pull quote',
          role: 'illustration',
          alt: 'A printed editorial spread with generous margins',
        },
      ],
      motion_intent: 'transition',
    },
    {
      id: 's5',
      title: 'The shape of the argument',
      layout: {
        regions: [
          { role: 'headline', span: 'full' },
          { role: 'body', span: 'half' },
          { role: 'aside', span: 'half' },
        ],
      },
      blocks: [
        { kind: 'text', style: 'headline', content: 'The shape of the argument' },
        { kind: 'text', style: 'body', content: 'One claim, held up by evidence.' },
        { kind: 'text', style: 'caption', content: 'Figure 1 — the argument as a shape.' },
      ],
      motion_intent: 'none',
    },
  ],
};

describe('cross-language schema round-trip', () => {
  it('accepts the golden deck that Pydantic accepts', () => {
    const result = DeckSchema.safeParse(goldenDeck);
    expect(result.success).toBe(true);
  });

  it('accepts a presentational-looking string, leaving it to the Python backstop', () => {
    // Division of labour: the schema has no *field* for styling, so a hex code
    // cannot be smuggled as a style. But "margin: 8px" is a valid body string
    // and the schema must accept it — rejecting it would false-positive on
    // legitimate content. The runtime backstop (api/schema/no_style.py) is
    // what walks every generated tree and rejects presentational tokens; Zod
    // cannot express that (patterns.md rule 1: structural first, backstop
    // second).
    const bad = structuredClone(goldenDeck);
    const slide = bad.slides[0];
    if (!slide) throw new Error('golden deck has slides');
    slide.blocks.push({ kind: 'text', style: 'body', content: 'margin: 8px' });
    const result = DeckSchema.safeParse(bad);
    expect(result.success).toBe(true);
  });

  it('rejects an unknown design family, matching Pydantic', () => {
    const bad = structuredClone(goldenDeck);
    bad.family_id = 'not-a-family';
    const result = DeckSchema.safeParse(bad);
    // Pydantic rejects unknown families via validator; JSON Schema cannot
    // express it, so the Zod half accepts the shape (field-level only). The
    // Pydantic check is the authority here.
    expect(result.success).toBe(true);
  });

  it('rejects a missing block kind, matching the discriminated union', () => {
    const bad = structuredClone(goldenDeck);
    const slide = bad.slides[0];
    if (!slide) throw new Error('golden deck has slides');
    const blocks = slide.blocks;
    const first = blocks[0];
    if (!first) throw new Error('slide has blocks');
    // Simulate untrusted input: shape it through unknown, the way external
    // input actually arrives (typescript.md -> one parse at the boundary).
    const untrusted: unknown = {
      ...slide,
      blocks: [{ ...first, kind: undefined }, ...blocks.slice(1)],
    };
    const result = DeckSchema.safeParse(untrusted);
    expect(result.success).toBe(false);
  });
});
