import { randomUUID } from 'node:crypto';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { expect, test } from '@playwright/test';

// Phase 13 — the scene as a stage. docs/v2/plan/13-scene-fit.md.
//
// The defect this file exists for was visible in the first generated
// experiences and invisible to everything else we had: a scene was exactly as
// tall as its content, so a four-word hero was roughly 40vh and a proof scene
// with a list was 130vh, and at every scroll position the viewport held the
// bottom of one scene and the top of the next. Every renderer test passed,
// because they assert structure and the structure was correct.
//
// These assertions need real layout, which is why they are here rather than in
// renderer.test.ts — `renderToStaticMarkup` can prove the declaration was
// emitted and cannot prove a scene owns the screen.

const ROOT = join(import.meta.dirname, '..', '.data', 'published');
const VIEWPORT = { width: 900, height: 600 };

test.use({ viewport: VIEWPORT });

function headlineScene(id: string, intent: string, text: string) {
  return {
    id,
    intent,
    layout: 'centered',
    blocks: [{ id: `b-${id}`, props: { type: 'headline', text } }],
  };
}

/** Deliberately taller than a 600px frame. The `mandatory` trap and the
 * never-clip rule both need a scene that genuinely does not fit, and a scene
 * that only *might* overflow makes this file's most important assertions pass
 * for the wrong reason.
 *
 * It is long *text* rather than many blocks because `Scene` caps a scene at 8
 * blocks — which is the schema doing its job, and worth knowing here: the
 * overflow this phase reports on is content that is too long, never content
 * that is too plentiful. */
function overlongScene(id: string) {
  // Under the 240-character cap `BodyProps` enforces, so the length here is
  // seven paragraphs rather than one long one.
  const paragraph = (n: number) =>
    `Paragraph ${n}. This scene carries more content than the frame can hold, which is the condition the floor has to survive: it grows rather than shrinking to fit, it is reported, and it is never clipped nor given a scrollbar.`;
  return {
    id,
    intent: 'proof',
    layout: 'stack',
    blocks: [
      {
        id: `b-${id}-h`,
        props: { type: 'headline', text: 'A scene that does not fit' },
      },
      ...Array.from({ length: 7 }, (_, i) => ({
        id: `b-${id}-${i}`,
        props: { type: 'body', text: paragraph(i + 1) },
      })),
    ],
  };
}

function artifact(artDirection: string, scenes: unknown[]) {
  return {
    title: 'Scene fit',
    mode: 'scroll',
    artDirection,
    scenes,
    publishedAt: new Date().toISOString(),
  };
}

const ids: string[] = [];

function seed(body: unknown): string {
  const id = randomUUID();
  mkdirSync(ROOT, { recursive: true });
  writeFileSync(join(ROOT, `${id}.json`), JSON.stringify(body), 'utf8');
  ids.push(id);
  return id;
}

let cinematicId: string;
let editorialId: string;

test.beforeAll(() => {
  cinematicId = seed(
    artifact('cinematic-dark', [
      headlineScene('one', 'hook', 'Four words only'),
      headlineScene('two', 'problem', 'The second scene'),
      overlongScene('three'),
      headlineScene('four', 'cta', 'The last scene'),
    ]),
  );
  editorialId = seed(
    artifact('editorial-light', [
      headlineScene('one', 'hook', 'A plate'),
      {
        id: 'two',
        intent: 'proof',
        layout: 'stack',
        blocks: [
          { id: 'b-two-h', props: { type: 'headline', text: 'A short table' } },
          { id: 'b-two-a', props: { type: 'body', text: 'One row.' } },
          { id: 'b-two-b', props: { type: 'body', text: 'Another row.' } },
        ],
      },
    ]),
  );
});

test.afterAll(() => {
  for (const id of ids) rmSync(join(ROOT, `${id}.json`), { force: true });
});

interface Box {
  id: string;
  top: number;
  bottom: number;
  clientHeight: number;
  scrollHeight: number;
}

const readBoxes = (page: import('@playwright/test').Page): Promise<Box[]> =>
  page.evaluate(() =>
    [...document.querySelectorAll('section[id^="scene-"]')].map((el) => {
      const r = el.getBoundingClientRect();
      return {
        id: el.id,
        top: r.top,
        bottom: r.bottom,
        clientHeight: el.clientHeight,
        scrollHeight: el.scrollHeight,
      };
    }),
  );

// The headline claim of the phase, and the one the user actually sees. Counted
// rather than eyeballed: at any scroll position, how many scene *boundaries*
// fall strictly inside the frame? A boundary inside the frame is two scenes
// sharing the screen. One is unavoidable while scrolling between scenes; two
// means a whole scene fits in the gap, which is the defect.
test('at most one scene boundary is visible in the frame, at every scroll position', async ({
  page,
}) => {
  await page.goto(`/p/${cinematicId}`);
  await expect(page.getByText('Four words only')).toBeVisible();

  const pageHeight = await page.evaluate(() => document.body.scrollHeight);
  const step = Math.floor(VIEWPORT.height / 3);

  for (let y = 0; y < pageHeight; y += step) {
    await page.evaluate((to) => window.scrollTo(0, to), y);
    const boxes = await readBoxes(page);
    // A boundary is a scene's top edge, excluding the document's own start and
    // anything flush with the frame edge — those are not two scenes sharing.
    const inside = boxes.filter((b) => b.top > 1 && b.top < VIEWPORT.height - 1);
    expect(
      inside.length,
      `scroll ${y}: boundaries inside the frame — ${inside.map((b) => b.id).join(', ')}`,
    ).toBeLessThanOrEqual(1);
  }
});

test('a viewport scene gets the frame as a floor, and an overlong one grows past it', async ({
  page,
}) => {
  await page.goto(`/p/${cinematicId}`);
  await expect(page.getByText('Four words only')).toBeVisible();
  const boxes = await readBoxes(page);
  expect(boxes).toHaveLength(4);

  // cinematic-dark answers `viewport` for all six layouts, so every scene is
  // at least the frame. Allow a pixel of rounding.
  for (const box of boxes) {
    expect(
      box.clientHeight,
      `${box.id} is shorter than the frame`,
    ).toBeGreaterThanOrEqual(VIEWPORT.height - 1);
  }

  // A floor, not a fixed height.
  const overlong = boxes.find((b) => b.id === 'scene-three');
  expect(overlong?.clientHeight).toBeGreaterThan(VIEWPORT.height);
});

// The rule that `block-size: 100svh` plus `overflow: auto` breaks, which is how
// products arrive at an inner scrollbar by accident. An inner scrollbar inside
// a scrolling page is the worst outcome available here, so it is asserted
// against the DOM rather than left to a screenshot.
test('no scene scrolls inside itself, and nothing is clipped', async ({ page }) => {
  await page.goto(`/p/${cinematicId}`);
  await expect(page.getByText('Four words only')).toBeVisible();

  for (const box of await readBoxes(page)) {
    expect(box.scrollHeight, `${box.id} has hidden overflow`).toBe(box.clientHeight);
  }

  // The last paragraph of the overlong scene is reachable, not cut off.
  await expect(page.getByText('Paragraph 7.')).toBeAttached();
});

// Half the perceived quality of the fit shell. A four-word hero in a
// full-height box placed at `start` is a headline stuck to the ceiling of an
// empty room; `cinematic-dark` places at `center`.
test('short content sits in the optical middle under cinematic-dark', async ({
  page,
}) => {
  await page.goto(`/p/${cinematicId}`);
  const headline = page.getByText('Four words only');
  await expect(headline).toBeVisible();

  const section = (await readBoxes(page))[0];
  const box = await headline.boundingBox();
  expect(section).toBeDefined();
  expect(box).not.toBeNull();
  if (!section || !box) return;

  const sceneCentre = section.top + section.clientHeight / 2;
  const textCentre = box.y + box.height / 2;
  // Generous, because the padding box is what it is centred against, not the
  // border box — the claim is "in the middle of the frame", not a pixel value.
  expect(Math.abs(textCentre - sceneCentre)).toBeLessThan(VIEWPORT.height * 0.15);
});

// The test that says `fit` is a token rather than a feature: two art
// directions give different answers about a scene's frame, and the renderer
// has one code path. `invariants.sh` check 7 is the other half — it fails if a
// viewport height is ever written as a constant in `renderer/`.
test('editorial-light lets a document-shaped scene run at content height', async ({
  page,
}) => {
  await page.goto(`/p/${editorialId}`);
  await expect(page.getByText('A plate')).toBeVisible();

  const boxes = await readBoxes(page);
  expect(boxes).toHaveLength(2);
  const [plate, table] = boxes;
  expect(plate).toBeDefined();
  expect(table).toBeDefined();
  if (!plate || !table) return;

  // `centered` is `viewport` for this direction; `stack` is `content`.
  expect(plate.clientHeight).toBeGreaterThanOrEqual(VIEWPORT.height - 1);
  expect(
    table.clientHeight,
    'a three-row stack padded to the full frame is the bug this token exists to avoid',
  ).toBeLessThan(VIEWPORT.height);
});
