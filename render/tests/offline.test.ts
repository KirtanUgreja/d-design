/**
 * Offline assertion — the exported file, opened for real.
 *
 * The other tests check that the HTML *contains* `connect-src 'none'`, which is
 * a string, not a fact: a stylesheet import, a font URL or an image that was
 * never inlined would still leave that line in the markup while the page
 * quietly fetched from the network. This opens the exported file from
 * `file://` in a real browser and fails on any request that leaves it — the
 * only version of the claim that cannot be satisfied by a passing string.
 */
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { chromium } from 'playwright';
import { describe, expect, it } from 'vitest';

import { renderDeckToHtml } from '../src/export.jsx';
import type { Deck } from '@web/schema/generated/Deck.js';

/** A deck with a generated image, so the data-URI path is on the page — an
 * image that failed to inline is the likeliest way this regresses. */
function deckWithImage(): Deck {
  return {
    family_id: 'editorial-serif',
    slides: [
      {
        id: 's1',
        title: 'A deck that travels alone',
        layout: {
          regions: [
            { role: 'headline', span: 'full', emphasis: 'primary' },
            { role: 'body', span: 'full' },
          ],
        },
        blocks: [
          { kind: 'text', style: 'headline', content: 'A deck that travels alone' },
          { kind: 'text', style: 'body', content: 'One file, opened from anywhere.' },
        ],
        motion_intent: 'reveal',
      },
      {
        id: 's2',
        title: 'With an image',
        layout: {
          regions: [
            { role: 'headline', span: 'full' },
            { role: 'media', span: 'full' },
          ],
        },
        blocks: [
          { kind: 'text', style: 'headline', content: 'With an image' },
          {
            kind: 'image',
            subject: 'An editorial spread',
            role: 'illustration',
            alt: 'An editorial spread',
          },
        ],
        motion_intent: 'none',
      },
    ],
  };
}

describe('the exported file, opened from file://', () => {
  it('makes no request that leaves the file', async () => {
    const html = renderDeckToHtml({
      deck: deckWithImage(),
      images: { s2: 'data:image/png;base64,iVBORw0KGgo=' },
      badge: true,
    });

    const dir = mkdtempSync(join(tmpdir(), 'dds-offline-'));
    const file = join(dir, 'deck.html');
    writeFileSync(file, html, 'utf8');

    const browser = await chromium.launch();
    try {
      const page = await browser.newPage();
      const escaped: string[] = [];
      page.on('request', (request) => {
        if (!request.url().startsWith('file://')) {
          escaped.push(request.url());
        }
      });

      await page.goto(`file://${file}`, { waitUntil: 'load' });
      // Deferred work (a CSS @import, a font, an onload fetch) would land after
      // `load`; give it a moment to try.
      await page.waitForTimeout(500);

      expect(escaped).toEqual([]);
    } finally {
      await browser.close();
    }
  }, 30_000);

  it('renders its content with no network available at all', async () => {
    const html = renderDeckToHtml({ deck: deckWithImage(), badge: true });

    const dir = mkdtempSync(join(tmpdir(), 'dds-offline-'));
    const file = join(dir, 'deck.html');
    writeFileSync(file, html, 'utf8');

    const browser = await chromium.launch();
    try {
      const page = await browser.newPage();
      // Nothing may load from the network: if the file needed it, this fails
      // loudly rather than rendering a blank page.
      await page.route('**/*', (route) =>
        route.request().url().startsWith('file://') ? route.continue() : route.abort(),
      );
      await page.goto(`file://${file}`, { waitUntil: 'load' });

      // Vitest's expect, not Playwright's: these are plain DOM assertions.
      const text = await page.locator('body').innerText();
      expect(text).toContain('A deck that travels alone');
      // The AI disclosure is part of the artefact, not chrome that a missing
      // script could drop.
      expect(await page.locator('[data-ai-disclosure="true"]').count()).toBeGreaterThan(0);
    } finally {
      await browser.close();
    }
  }, 30_000);
});
