/**
 * Export tests — the single-file guarantee (phase 05).
 *
 * The artefact must: be one self-contained .html, make zero network requests
 * (connect-src 'none'), be complete without JS (progressive enhancement), and
 * have slide-based navigation (arrow keys, buttons, counter — no scroll).
 * The zero-request assertion in a real browser is the Playwright job (phase
 * 08/CI); here we assert the static guarantees the file must carry.
 */
import { describe, expect, it } from 'vitest';

import { renderDeckToHtml } from '../src/export.jsx';
import type { Deck } from '@web/schema/generated/Deck.js';

function sampleDeck(): Deck {
  return {
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
          { kind: 'text', style: 'body', content: 'A deck that reads as authored.' },
        ],
      },
      {
        id: 's2',
        title: 'The numbers',
        layout: {
          regions: [
            { role: 'headline', span: 'full' },
            { role: 'quote', span: 'full' },
          ],
        },
        blocks: [
          { kind: 'text', style: 'headline', content: 'The numbers' },
          { kind: 'quote', text: 'A single idea, held up by evidence.', attribution: 'The author' },
        ],
      },
    ],
  };
}

describe('renderDeckToHtml', () => {
  it('produces one self-contained html document', () => {
    const html = renderDeckToHtml({ deck: sampleDeck() });
    expect(html.startsWith('<!DOCTYPE html>')).toBe(true);
    expect(html).toContain('</html>');
    // The renderer's slides are in the markup (complete without JS).
    expect(html).toContain('The quiet power of editorial design');
    expect(html).toContain('dds-region');
  });

  it('enforces connect-src none — the file talks to nothing', () => {
    const html = renderDeckToHtml({ deck: sampleDeck() });
    expect(html).toContain("connect-src 'none'");
    // No external http(s) URL anywhere in the artefact.
    expect(html).not.toMatch(/https?:\/\/(?!example\.com)/);
    expect(html).toContain('img-src data:');
  });

  it('is complete without JS — the deck is in the markup, nav is enhancement', () => {
    const html = renderDeckToHtml({ deck: sampleDeck() });
    // If JS never runs, a viewer sees the deck (first slide visible, rest
    // present in the DOM), not an empty shell.
    expect(html).toContain('<section');
    expect(html).toContain('id="dds-counter"');
    expect(html).toContain('id="dds-prev"');
    expect(html).toContain('id="dds-next"');
    // Nav behavior is keyboard + swipe, not scroll.
    expect(html).toContain('ArrowRight');
    expect(html).toContain('touchstart');
    expect(html).not.toContain('overflow-y: scroll');
  });

  it('inlines a generated image as a data URI', () => {
    const d = sampleDeck();
    const first = d.slides[0];
    if (!first) throw new Error('deck has a slide');
    first.layout.regions = [
      { role: 'headline', span: 'full' },
      { role: 'media', span: 'full' },
    ];
    first.blocks = [
      { kind: 'text', style: 'headline', content: 'A hero' },
      { kind: 'image', subject: 'A hero visual', role: 'hero', alt: 'Hero visual' },
    ];
    const html = renderDeckToHtml({
      deck: d,
      images: { s1: 'data:image/png;base64,QUJD' },
    });
    expect(html).toContain('data:image/png;base64,QUJD');
    expect(html).toContain('alt="Hero visual"');
  });

  it('inlines the renderer stylesheet and family tokens', () => {
    const html = renderDeckToHtml({ deck: sampleDeck() });
    expect(html).toContain('--dds-font-display');
    expect(html).toContain('.dds-slide');
  });

  it('throws on an unknown family', () => {
    const bad = sampleDeck();
    bad.family_id = 'nope';
    expect(() => renderDeckToHtml({ deck: bad })).toThrow(/unknown design family/);
  });
});
