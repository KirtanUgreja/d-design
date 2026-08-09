import { randomUUID } from 'node:crypto';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { expect, test } from '@playwright/test';

// Phase 15 — images that exist. docs/v2/plan/15-images.md.
//
// For the whole of v1 an `Image` block rendered a flat grey rectangle and
// nothing else, which is most of why generated output looked thin. The first
// assertion in this file is simply that an uploaded photograph appears.
//
// Needs a running `api` with at least one uploaded image, because the point is
// the real resolution path — `/a/{id}` on the web origin, proxying to `api`,
// serving bytes that went through magic-byte verification and re-encode.

const ROOT = join(import.meta.dirname, '..', '.data', 'published');
const ASSET_ID = process.env.TEST_ASSET_ID ?? '';

test.use({ viewport: { width: 1200, height: 800 } });

const ids: string[] = [];

function seed(artDirection: string): string {
  const id = randomUUID();
  mkdirSync(ROOT, { recursive: true });
  writeFileSync(
    join(ROOT, `${id}.json`),
    JSON.stringify({
      title: 'Images',
      mode: 'scroll',
      artDirection,
      scenes: [
        {
          id: 'one',
          intent: 'hook',
          layout: 'centered',
          blocks: [
            {
              id: 'b-img',
              props: {
                type: 'image',
                assetId: ASSET_ID,
                alt: 'An uploaded photograph',
                fit: 'cover',
                treatment: 'plain',
              },
            },
          ],
        },
      ],
      publishedAt: new Date().toISOString(),
    }),
  );
  ids.push(id);
  return id;
}

test.afterAll(() => {
  for (const id of ids) rmSync(join(ROOT, `${id}.json`), { force: true });
});

test.skip(ASSET_ID === '', 'needs TEST_ASSET_ID from a running api');

test('an uploaded photograph renders, from a same-origin path', async ({ page }) => {
  const id = seed('cinematic-dark');
  const requested: string[] = [];
  page.on('request', (r) => requested.push(r.url()));

  await page.goto(`/p/${id}`);
  const img = page.locator('img').first();
  await expect(img).toBeVisible();

  // Same origin. The published page's CSP can be `img-src 'self'` only if the
  // renderer never composes a URL on another host.
  const src = await img.getAttribute('src');
  expect(src).toBe(`/a/${ASSET_ID}`);

  // Decoded, not a broken-image glyph. `naturalWidth` is 0 for a failed load,
  // and a 404 through the proxy would look identical to the eye at this size.
  await expect
    .poll(() => img.evaluate((el: HTMLImageElement) => el.naturalWidth), {
      timeout: 5000,
    })
    .toBeGreaterThan(100);

  // Nothing reached the api origin directly from the page.
  expect(requested.filter((u) => u.includes(':8000'))).toEqual([]);
});

test('the box is reserved before the image loads, so nothing shifts', async ({
  page,
}) => {
  const id = seed('cinematic-dark');
  await page.goto(`/p/${id}`);
  const box = page.locator('img').first().locator('..');
  // cinematic-dark's first ratio is 21:9. The wrapper takes it from the token,
  // so the space exists before a byte of image arrives — which is what stops a
  // viewport-fit scene from reflowing when the image decodes.
  const ratio = await box.evaluate((el) => getComputedStyle(el).aspectRatio);
  expect(ratio.replace(/\s/g, '')).toBe('21/9');
});

test('one photograph reads differently under two art directions', async ({ page }) => {
  // The reskin claim, at its strongest: same asset, same tree, no re-encode
  // and no second asset row — only the treatment token changed.
  await page.goto(`/p/${seed('cinematic-dark')}`);
  const cine = await page
    .locator('img')
    .first()
    .evaluate((el) => getComputedStyle(el).filter);

  await page.goto(`/p/${seed('editorial-light')}`);
  const edit = await page
    .locator('img')
    .first()
    .evaluate((el) => getComputedStyle(el).filter);

  // duotone greyscales and lifts contrast; as-shot does neither.
  expect(cine).toContain('grayscale');
  expect(edit === 'none' || !edit.includes('grayscale')).toBe(true);
  expect(cine).not.toBe(edit);
});
