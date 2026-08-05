import { randomUUID } from 'node:crypto';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { expect, test } from '@playwright/test';

// docs/v1/plan/05-publish-present-embed.md -> Verify, the rows that go live
// here. Seeds the artifact directly on disk rather than through `api` — the
// serving path under test (storage.ts -> page.tsx) never talks to `api` at
// view time, so these tests shouldn't need a live one either.

const ROOT = join(import.meta.dirname, '..', '.data', 'published');

const ARTIFACT = {
  title: 'Security Test',
  mode: 'scroll',
  artDirection: 'cinematic-dark',
  scenes: [
    {
      id: 's1',
      intent: 'hook',
      layout: 'centered',
      blocks: [
        { id: 'b1', props: { type: 'headline', text: 'Zero requests, by design' } },
      ],
    },
    {
      id: 's2',
      intent: 'cta',
      layout: 'centered',
      blocks: [
        {
          id: 'b2',
          props: {
            type: 'cta',
            label: 'Go',
            href: 'https://example.com',
            style: 'primary',
          },
        },
      ],
    },
  ],
  publishedAt: new Date().toISOString(),
};

let id: string;

test.beforeAll(() => {
  id = randomUUID();
  mkdirSync(ROOT, { recursive: true });
  writeFileSync(join(ROOT, `${id}.json`), JSON.stringify(ARTIFACT), 'utf8');
});

test.afterAll(() => {
  rmSync(join(ROOT, `${id}.json`), { force: true });
});

test('the published page issues no fetch/XHR call — connect-src none genuinely holds', async ({
  page,
}) => {
  // The page's own JS/CSS/font assets are expected requests (a real browser
  // loading a real page); `connect-src 'none'` is a claim about calls the
  // page's own script logic makes, not about total network activity. This
  // is the assertion techstack/frontend.md and the CSP header actually make.
  const dynamicRequests: string[] = [];
  page.on('request', (r) => {
    if (r.resourceType() === 'fetch' || r.resourceType() === 'xhr') {
      dynamicRequests.push(r.url());
    }
  });

  await page.goto(`/p/${id}`);
  await page.getByText('Zero requests, by design').waitFor();
  await page.waitForTimeout(500); // past the reveal transition, so nothing async is still settling

  expect(dynamicRequests).toEqual([]);
});

test('CSP is correct on the published response', async ({ request }) => {
  const res = await request.get(`/p/${id}`);
  const csp = res.headers()['content-security-policy'];
  expect(csp).toContain("connect-src 'none'");
  expect(csp).toContain('frame-ancestors *');
  expect(res.headers()['x-content-type-options']).toBe('nosniff');
  expect(res.headers()['referrer-policy']).toBe('no-referrer');
});

test('CSP is correct on the embed response', async ({ request }) => {
  const res = await request.get(`/e/${id}`);
  const csp = res.headers()['content-security-policy'];
  expect(csp).toContain("connect-src 'none'");
  expect(csp).toContain('frame-ancestors *');
});

test('app routes carry frame-ancestors none', async ({ request }) => {
  const res = await request.get('/');
  expect(res.headers()['content-security-policy']).toContain("frame-ancestors 'none'");
});

test('a guessed sub-path under the published id 404s, nothing cached', async ({
  request,
}) => {
  const css = await request.get(`/p/${id}/x.css`);
  expect(css.status()).toBe(404);
  const jpg = await request.get(`/p/${id}/x.jpg`);
  expect(jpg.status()).toBe(404);
});

test('an unpublished/unknown id renders the designed empty state, not a framework 404 page', async ({
  page,
}) => {
  await page.goto('/p/00000000-0000-4000-8000-000000000000');
  await expect(page.getByText("This page isn't available.")).toBeVisible();
});

test('the published page is readable with JavaScript disabled', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto(`/p/${id}`);
  await expect(page.getByText('Zero requests, by design')).toBeVisible();
  const opacity = await page
    .getByText('Zero requests, by design')
    .evaluate((el) => getComputedStyle(el).opacity);
  expect(opacity).toBe('1');
  await context.close();
});
