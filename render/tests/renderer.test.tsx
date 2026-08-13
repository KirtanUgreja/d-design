/**
 * Renderer tests — the renderer produces HTML for every archetype, and the
 * same (deck, family) input produces stable markup (the byte-identity seed of
 * the editor/export guarantee). No snapshot: we assert structure, not pixels
 * (tooling.md: a snapshot on a design surface fails on every intentional
 * improvement).
 */
import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';

import { DeckRenderer } from '@web/features/renderer/index.js';
import { familyTokens } from '@web/features/design-system/index.js';
import type { Deck, Slide } from '@web/schema/generated/Deck.js';

function slide(id: string, archetype: string, blocks: unknown[]): Slide {
  return {
    id,
    title: `Slide ${id}`,
    layout_archetype: archetype,
    blocks: blocks as Slide['blocks'],
  };
}

function deck(archetypes: string[]): Deck {
  return {
    family_id: 'editorial-serif',
    slides: archetypes.map((a, i) =>
      slide(`s${i + 1}`, a, [
        { kind: 'text', style: 'headline', content: `Headline ${i + 1}` },
        { kind: 'text', style: 'body', content: 'Some body copy.' },
      ]),
    ),
  };
}

const ALL_ARCHETYPES = [
  'opener',
  'statement',
  'section',
  'split',
  'columns',
  'list',
  'stats',
  'quote',
  'image',
  'callout',
  'quote-image',
  'closer',
];

describe('DeckRenderer', () => {
  it('renders every archetype without throwing', () => {
    const motion = familyTokens('editorial-serif')?.motion;
    expect(motion).toBeDefined();
    const html = renderToStaticMarkup(
      <DeckRenderer deck={deck(ALL_ARCHETYPES)} motion={motion!} />,
    );
    for (const a of ALL_ARCHETYPES) {
      expect(html).toContain(`dds-slide--${a}`);
    }
  });

  it('renders the headline first and the cta', () => {
    const d = deck(['opener', 'closer']);
    const closer = d.slides[1];
    if (!closer) throw new Error('deck has a closer');
    closer.cta = { label: 'Sign up', destination: 'https://example.com' };
    const html = renderToStaticMarkup(
      <DeckRenderer deck={d} motion={familyTokens('editorial-serif')!.motion} />,
    );
    expect(html).toContain('Headline 1');
    expect(html).toContain('Sign up');
    expect(html).toContain('https://example.com');
  });

  it('inlines a generated image as a data URI', () => {
    const d = deck(['image']);
    const first = d.slides[0];
    if (!first) throw new Error('deck has a slide');
    first.blocks = [
      { kind: 'text', style: 'headline', content: 'Hero' },
      { kind: 'image', subject: 'A hero visual', role: 'hero', alt: 'Hero visual' },
    ];
    const html = renderToStaticMarkup(
      <DeckRenderer
        deck={d}
        motion={familyTokens('editorial-serif')!.motion}
        images={{ s1: 'data:image/png;base64,QUJD' }}
      />,
    );
    expect(html).toContain('data:image/png;base64,QUJD');
    expect(html).toContain('alt="Hero visual"');
  });

  it('renders a chart from its series', () => {
    const d = deck(['stats']);
    const first = d.slides[0];
    if (!first) throw new Error('deck has a slide');
    first.blocks = [
      { kind: 'text', style: 'headline', content: 'The data' },
      {
        kind: 'chart',
        chart_type: 'bar',
        title: 'Growth',
        series: [
          { label: 'Q1', value: 10 },
          { label: 'Q2', value: 25 },
        ],
      },
    ];
    const html = renderToStaticMarkup(
      <DeckRenderer deck={d} motion={familyTokens('editorial-serif')!.motion} />,
    );
    expect(html).toContain('dds-chart');
    expect(html).toContain('Q1');
    expect(html).toContain('Growth');
  });

  it('throws on an unknown family (a pipeline bug, not a render choice)', () => {
    const bad = deck(['opener']);
    bad.family_id = 'does-not-exist';
    expect(() =>
      renderToStaticMarkup(
        <DeckRenderer deck={bad} motion={familyTokens('editorial-serif')!.motion} />,
      ),
    ).toThrow(/unknown design family/);
  });
});
