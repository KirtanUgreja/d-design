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
const API = process.env.API_URL ?? 'http://localhost:8000';

// A 600x400 PNG, uploaded by this file through the real `POST /assets` — magic
// bytes, re-encode, both renditions, a real row.
//
// Self-seeding on purpose. This spec first took an asset id from the
// environment, and the id kept evaporating: the `api` test suite truncates
// tables, so any run of `pytest` between seeding and this file left it
// pointing at a row that no longer existed. A test whose fixture another
// suite can delete is a test that reports someone else's cleanup as a product
// defect — which it did, twice.
//
// Wider than `THUMB_WIDTH` (480) so a small rendition actually gets made;
// noisy rather than flat so it does not compress to something degenerate.
const FIXTURE_PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAlgAAAGQCAIAAAD9V4nPAAAE2UlEQVR42u3VMQ0AIADAsBEg+HeMCT6aVMGejeo0AeBPqz0LAD5lhAAYoRAAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEARmiEABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghAEaoAgBGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCABGCIARGiEARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARggARgiAEaoAgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECgBECYIRCAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEABihEQJghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghABghAAYoQoAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAGCEAvHMB474bjHcVaCQAAAAASUVORK5CYII=';

let ASSET_ID = '';

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

test.beforeAll(async () => {
  const body = new FormData();
  body.set(
    'file',
    new Blob([Uint8Array.from(atob(FIXTURE_PNG), (c) => c.charCodeAt(0))], {
      type: 'image/png',
    }),
    'fixture.png',
  );
  const res = await fetch(`${API}/assets`, { method: 'POST', body });
  if (!res.ok) throw new Error(`seeding an asset needs a running api (${res.status})`);
  ASSET_ID = ((await res.json()) as { id: string }).id;
});

test.afterAll(() => {
  for (const id of ids) rmSync(join(ROOT, `${id}.json`), { force: true });
});

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

test('a second, narrower rendition is offered through srcset', async ({ page }) => {
  const id = seed('cinematic-dark');
  await page.goto(`/p/${id}`);
  const img = page.locator('img').first();
  await expect(img).toBeVisible();

  // Both candidates, and the small one is a derivable path rather than a
  // lookup — which is what keeps the renderer pure.
  const srcset = await img.getAttribute('srcset');
  expect(srcset).toBe(`/a/${ASSET_ID}/sm 480w, /a/${ASSET_ID} 1600w`);
  expect(await img.getAttribute('sizes')).toBeTruthy();

  // Both candidates resolve to a real image. Whether this particular fixture
  // *has* a distinct small rendition is deliberately not asserted here —
  // `test_a_rendition_that_is_not_smaller_in_bytes_is_discarded` covers that,
  // and it is exactly the case where the answer is "no". What matters at this
  // level is that neither URL a browser might choose can 404: `/sm` falls back
  // to the full-size object when there is nothing narrower to serve.
  const [large, small] = await Promise.all([
    page.request.get(`/a/${ASSET_ID}`),
    page.request.get(`/a/${ASSET_ID}/sm`),
  ]);
  for (const res of [large, small]) {
    expect(res.status()).toBe(200);
    expect(res.headers()['content-type']).toContain('image/');
  }
});

test('the proxy serves two paths and refuses everything else', async ({ page }) => {
  // A proxy that forwards whatever path it is handed will eventually forward
  // one it should not, so the shape is an allowlist rather than a pass-through.
  for (const path of [
    `/a/${ASSET_ID}/xl`,
    `/a/${ASSET_ID}/sm/extra`,
    `/a/${ASSET_ID}/../assets`,
    '/a/not-a-uuid',
  ]) {
    const res = await page.request.get(path, { maxRedirects: 0 });
    expect(res.status(), path).not.toBe(200);
  }
});
