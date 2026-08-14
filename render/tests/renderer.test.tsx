/**
 * Renderer tests — the renderer produces HTML for every region role and span,
 * and the same (deck, family) input produces stable markup (the byte-identity
 * seed of the editor/export guarantee). No snapshot: we assert structure, not
 * pixels (tooling.md: a snapshot on a design surface fails on every
 * intentional improvement).
 *
 * Phase 10: the renderer is grammar-driven — it renders whatever layout the
 * schema carries, mapping each region to a grid cell. There is no catalogue
 * of archetypes to enumerate; every region role and span must render.
 */
import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';

import { DeckRenderer } from '@web/features/renderer/index.js';
import { familyTokens } from '@web/features/design-system/index.js';
import type { Deck, LayoutRegion, Slide } from '@web/schema/generated/Deck.js';

function slide(id: string, regions: LayoutRegion[], blocks: unknown[]): Slide {
  return {
    id,
    title: `Slide ${id}`,
    layout: { regions },
    blocks: blocks as Slide['blocks'],
  };
}

const ALL_ROLES = ['headline', 'body', 'media', 'stats', 'quote', 'chart', 'aside'] as const;
const ALL_SPANS = ['full', 'two-thirds', 'half', 'third', 'quarter'] as const;

function deck(regions: LayoutRegion[]): Deck {
  return {
    family_id: 'editorial-serif',
    slides: [
      slide('s1', regions, [
        { kind: 'text', style: 'headline', content: 'The headline' },
        { kind: 'text', style: 'body', content: 'Some body copy.' },
      ]),
    ],
  };
}

describe('DeckRenderer', () => {
  it('renders every region role and span without throwing', () => {
    const motion = familyTokens('editorial-serif')?.motion;
    expect(motion).toBeDefined();
    const allRegions: LayoutRegion[] = [
      ...ALL_ROLES.map((role) => ({ role, span: 'full' as const })),
      ...ALL_SPANS.map((span) => ({ role: 'body' as const, span })),
    ];
    const html = renderToStaticMarkup(<DeckRenderer deck={deck(allRegions)} motion={motion!} />);
    for (const role of ALL_ROLES) {
      expect(html).toContain(`data-role="${role}"`);
    }
    for (const span of ALL_SPANS) {
      expect(html).toContain(`data-span="${span}"`);
    }
  });

  it('renders the headline first and the cta', () => {
    const d = deck([{ role: 'headline', span: 'full' }]);
    const first = d.slides[0];
    if (!first) throw new Error('deck has a slide');
    first.cta = { label: 'Sign up', destination: 'https://example.com' };
    const html = renderToStaticMarkup(
      <DeckRenderer deck={d} motion={familyTokens('editorial-serif')!.motion} />,
    );
    expect(html).toContain('The headline');
    expect(html).toContain('Sign up');
    expect(html).toContain('https://example.com');
  });

  it('inlines a generated image as a data URI', () => {
    const d = deck([{ role: 'headline', span: 'full' }]);
    const first = d.slides[0];
    if (!first) throw new Error('deck has a slide');
    first.layout.regions = [
      { role: 'headline', span: 'full' },
      { role: 'media', span: 'full' },
    ];
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

  it('renders a chart as SVG from its series', () => {
    const d = deck([{ role: 'headline', span: 'full' }]);
    const first = d.slides[0];
    if (!first) throw new Error('deck has a slide');
    first.layout.regions = [
      { role: 'headline', span: 'full' },
      { role: 'chart', span: 'full' },
    ];
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
    expect(html).toContain('<svg');
    expect(html).toContain('Q1');
    expect(html).toContain('Growth');
    // No presentational value from the model — colours come from the family
    // tokens (var() references), never a hex from the deck.
    expect(html).not.toMatch(/#[0-9a-f]{3,8}/i);
  });

  it('renders every chart type as SVG without throwing', () => {
    const motion = familyTokens('editorial-serif')!.motion;
    for (const chartType of ['bar', 'line', 'donut'] as const) {
      const d = deck([
        { role: 'headline', span: 'full' },
        { role: 'chart', span: 'full' },
      ]);
      const first = d.slides[0];
      if (!first) throw new Error('deck has a slide');
      first.blocks = [
        { kind: 'text', style: 'headline', content: 'The data' },
        {
          kind: 'chart',
          chart_type: chartType,
          title: `A ${chartType} chart`,
          series: [
            { label: 'A', value: 10 },
            { label: 'B', value: 25 },
            { label: 'C', value: 15 },
          ],
        },
      ];
      const html = renderToStaticMarkup(<DeckRenderer deck={d} motion={motion} />);
      expect(html).toContain('<svg');
      expect(html).toContain(`data-chart="${chartType}"`);
    }
  });

  it('throws on an unknown family (a pipeline bug, not a render choice)', () => {
    const bad = deck([{ role: 'headline', span: 'full' }]);
    bad.family_id = 'does-not-exist';
    expect(() =>
      renderToStaticMarkup(
        <DeckRenderer deck={bad} motion={familyTokens('editorial-serif')!.motion} />,
      ),
    ).toThrow(/unknown design family/);
  });
});
