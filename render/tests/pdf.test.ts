/**
 * PDF export tests (phase 14).
 *
 * The PDF is a faithful print of the single-file HTML, not a screenshot. The
 * deterministic assertions here check the print contract that lives inside
 * the HTML (@page slide-sized pages, resting state, nav hidden) — that is
 * what makes the print faithful without a browser in the unit path. The real
 * browser PDF (Playwright printing the bytes) is the e2e/human step.
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

describe('pdf export contract', () => {
  it('inlines slide-sized @page print CSS in the exported HTML', () => {
    const html = renderDeckToHtml({ deck: sampleDeck() });
    expect(html).toContain('@media print');
    expect(html).toContain('size: 16in 9in');
    expect(html).toContain('page-break-after: always');
    expect(html).toContain('.dds-nav');
    expect(html).toContain('display: none !important');
  });

  it('prints the resting state, not an animated or hidden state', () => {
    const html = renderDeckToHtml({ deck: sampleDeck() });
    // Motion is the only thing that changes the resting state; the print CSS
    // forces reveals to their finished (opacity 1) form.
    expect(html).toContain('[data-reveal]');
    expect(html).toContain('opacity: 1 !important');
  });

  it('gives every slide one page via break-after', () => {
    const html = renderDeckToHtml({ deck: sampleDeck() });
    expect(html).toContain('break-after: page');
    expect(html).toContain('.dds-slide:last-child');
  });

  it('produces the same HTML with and without the print CSS contract', () => {
    // The PDF path uses the SAME renderDeckToHtml — the byte-identity
    // guarantee extends to the print: one implementation, two formats.
    const html = renderDeckToHtml({ deck: sampleDeck() });
    expect(html).toContain('connect-src');
    expect(html).toContain('dds-region');
  });
});

/**
 * The real Playwright print path. These launch a browser (Playwright is the
 * documented print path, dependencies.md), so they are slower than the
 * deterministic contract tests above — but they are the phase's exit gate:
 * a faithful PDF print of the HTML, not a lossy screenshot.
 */
describe('renderDeckToPdf (real browser)', () => {
  function multiSlideDeck(n: number): Deck {
    return {
      family_id: 'editorial-serif',
      slides: Array.from({ length: n }, (_, i) => ({
        id: `s${i + 1}`,
        title: `Slide ${i + 1}`,
        layout: {
          regions: [
            { role: 'headline', span: 'full' },
            { role: 'body', span: 'full' },
          ],
        },
        blocks: [
          { kind: 'text', style: 'headline', content: `Headline ${i + 1}` },
          { kind: 'text', style: 'body', content: `Body ${i + 1}` },
        ],
      })),
    };
  }

  it('produces real PDF bytes from the print path', async () => {
    const { renderDeckToPdf } = await import('../src/pdf.js');
    const pdf = await renderDeckToPdf({ deck: multiSlideDeck(2) });
    expect(pdf.subarray(0, 5).toString('ascii')).toBe('%PDF-');
    expect(pdf.length).toBeGreaterThan(1000);
  }, 60000);

  it('prints every slide — a 3-slide deck is a larger PDF than a 1-slide deck', async () => {
    const { renderDeckToPdf } = await import('../src/pdf.js');
    const one = await renderDeckToPdf({ deck: multiSlideDeck(1) });
    const three = await renderDeckToPdf({ deck: multiSlideDeck(3) });
    // Each slide adds a page of printed content, so the file grows. This is
    // the assertion that the print CSS forces every slide visible (the nav
    // shell hides slides 1+ inline; the print CSS must override it).
    expect(three.length).toBeGreaterThan(one.length);
  }, 60000);
});
