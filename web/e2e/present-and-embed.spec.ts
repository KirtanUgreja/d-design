import { randomUUID } from 'node:crypto';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { createServer, type Server } from 'node:http';
import { join } from 'node:path';

import { expect, test } from '@playwright/test';

// The two rows of docs/v1/spec.md -> Verification's end-to-end line that
// nothing else covers: presenting, and being embedded. Both were written,
// neither had ever been exercised end to end, and the v1 acceptance run found
// a real bug in the first one — see the fullscreen test's comment.
//
// Seeded on disk like publish-security.spec.ts, and for the same reason: the
// serving path never talks to `api` at view time, so these should not need a
// live one. Three scenes, each a full viewport tall, because navigation is the
// thing under test and it needs somewhere to navigate to.

const ROOT = join(import.meta.dirname, '..', '.data', 'published');

function scene(id: string, intent: string, text: string) {
  return {
    id,
    intent,
    layout: 'centered',
    blocks: [{ id: `b-${id}`, props: { type: 'headline', text } }],
  };
}

const ARTIFACT = {
  title: 'Present and Embed',
  mode: 'scroll',
  artDirection: 'cinematic-dark',
  scenes: [
    scene('one', 'hook', 'The first scene'),
    scene('two', 'problem', 'The second scene'),
    {
      id: 'three',
      intent: 'cta',
      layout: 'centered',
      blocks: [
        {
          id: 'b-three',
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
/** A blank HTML page on a *network* origin, which is what an embed actually
 * lives on. Not a `file://` page: `frame-ancestors *` matches network schemes
 * only, so a local .html file is refused — the obvious way to hand-check
 * "embed in a blank HTML page" is the one way that cannot work, and finding
 * that out from a blocked frame rather than from here costs an afternoon. */
let host: Server;
/** Port 0, not a fixed number. `fullyParallel` splits this file's tests across
 * workers and each one runs `beforeAll`, so a hardcoded port is three
 * processes racing for one socket — which is exactly what happened. */
let hostUrl: string;

test.beforeAll(async () => {
  id = randomUUID();
  mkdirSync(ROOT, { recursive: true });
  writeFileSync(join(ROOT, `${id}.json`), JSON.stringify(ARTIFACT), 'utf8');

  const body = `<!doctype html><meta charset="utf-8"><title>blank</title>
    <iframe id="embedded" src="http://localhost:3100/e/${id}" width="900" height="600" style="border:0"></iframe>`;
  host = createServer((_req, res) => {
    res.writeHead(200, { 'content-type': 'text/html' });
    res.end(body);
  });
  await new Promise<void>((resolve) => host.listen(0, resolve));
  const address = host.address();
  if (address === null || typeof address === 'string') {
    throw new Error('the embed host did not get a TCP port');
  }
  hostUrl = `http://localhost:${address.port}/`;
});

test.afterAll(async () => {
  rmSync(join(ROOT, `${id}.json`), { force: true });
  await new Promise<void>((resolve) => host.close(() => resolve()));
});

// docs/v1/spec.md -> Risk 3: fullscreen plus keyboard nav is the minimum that
// keeps the word "presentation" honest. It was not honest.
//
// Fullscreen makes the container the whole screen with the UA's `overflow:
// visible`, so every scene after the first overflowed a box nothing could
// scroll — the document behind it cannot scroll either, being painted over.
// The keydown handler fired and `scrollIntoView` ran, and the page did not
// move. Both halves worked; the pair had never been run.
//
// Asserted on where the *second scene* ends up, not on a scroll offset: the
// claim is "arrow keys move between scenes", and a scrollTop that changed by
// some number of pixels is not that claim.
test('fullscreen, and arrow keys move between scenes', async ({ page }) => {
  await page.goto(`/p/${id}`);
  await page.getByRole('button', { name: 'Present' }).click();

  // The button flipping to Exit is the component's own `isFullscreen` state,
  // which is what arms the keydown handler — a stronger check than
  // `document.fullscreenElement`, which can be non-null for some other element.
  await expect(page.getByRole('button', { name: 'Exit' })).toBeVisible();

  const secondSceneTop = () =>
    page.evaluate(() =>
      Math.round(
        document.getElementById('scene-two')?.getBoundingClientRect().top ?? NaN,
      ),
    );

  expect(await secondSceneTop()).toBeGreaterThan(100);

  await page.keyboard.press('ArrowDown');
  // Not flush with the viewport top, and that is the fix rather than a
  // regression. This asserted `< 10` until phase 13, which is the position
  // that put the first line of every scene underneath the fixed control pill —
  // `scrollIntoView` aligns the top edge, and the pill occupies that edge.
  // `scroll-margin-block-start` (the art direction's `fitScrollMargin`, 4rem)
  // offsets both this and the snap position with one declaration, so the
  // landing spot is the scroll-margin box rather than the border box.
  //
  // Asserted as a band against the *pill*, not against the number 64: the
  // claim is "the scene lands flush and the chrome is clear of it", and a
  // literal would turn a token change into a test failure that says nothing.
  const pillBottom = await page.evaluate(
    () => document.querySelector('button')?.getBoundingClientRect().bottom ?? Number.NaN,
  );
  // Poll on the condition that *converges* — the scene arriving near the top.
  // Polling on "below the pill" instead is satisfied by the pre-scroll state,
  // where the scene sits a whole frame away, so it passes before the scroll
  // has begun and the next assertion reads the old position.
  await expect.poll(secondSceneTop, { timeout: 3000 }).toBeLessThan(120);
  expect(await secondSceneTop()).toBeGreaterThan(pillBottom);

  await page.keyboard.press('ArrowUp');
  await expect.poll(secondSceneTop, { timeout: 3000 }).toBeGreaterThan(300);
});

test('it renders inside an iframe on a blank HTML page from another origin', async ({
  page,
}) => {
  await page.goto(hostUrl);

  // Real rendered content through the real renderer, not a 200 — an iframe
  // that loaded an error page is still an iframe that loaded.
  const embedded = page.frameLocator('#embedded');
  await expect(embedded.getByText('The first scene')).toBeVisible();
});

// docs/v1/plan/README.md -> "Every `Image` has non-empty `alt`". The schema
// already makes an empty one unrepresentable (`alt: str = Field(min_length=1)`),
// so this is the other half: that the renderer actually emits it, on every
// image, rather than dropping the field on the way to the DOM.
test('every image the renderer emits carries a non-empty alt', async ({ page }) => {
  await page.goto('/dev/primitives');
  const images = page.locator('img');
  const count = await images.count();
  expect(count).toBeGreaterThan(0);

  for (let i = 0; i < count; i++) {
    expect((await images.nth(i).getAttribute('alt'))?.trim()).toBeTruthy();
  }
});
