import { expect, test } from '@playwright/test';

// docs/v1/plan/09-editor.md -> Verify, hot path 3: "A keystroke in the panel
// re-renders one block, not the tree. Check with the profiler, not by feel."
// and the exit gate's "Editing feels instant".
//
// "By feel" is exactly what this file exists to avoid. It measures the half of
// the claim a browser can actually answer: how long a keystroke takes to reach
// the page, which is what "instant" means to the person typing.
//
// The other half — that a keystroke re-renders one block rather than the tree —
// is asserted in `src/features/editor/editor.test.ts`, on the store, where the
// property actually lives: untouched blocks come back from `applyPatch` by
// reference. Those two tests fail when structural sharing breaks; this one does
// not, and it is worth saying why rather than leaving someone to add a weaker
// version of it here again.
//
// **DOM node identity is not a proxy for a re-render, and was tried.** An
// earlier version of this file stashed every `[data-block-id]` element, edited
// one block, and asserted none of the others had been replaced. It passed with
// structural sharing deliberately broken — React reconciles by position and
// reuses the DOM node whether or not the props object is new, so a re-render
// that produces identical output leaves no trace in the DOM at all. The test
// looked like a strong structural claim and could not fail.
//
// Runs against `next build` (playwright.config.ts), which is the honest
// target — the React Compiler's memoization is a production build's behaviour.

const SETTLE_MS = 400;

test('a panel keystroke reaches the page well inside the instant threshold', async ({
  page,
}) => {
  await page.goto('/edit/e2e-latency');

  const headline = page.getByRole('heading', { level: 2 }).first();
  await expect(headline).toBeVisible();
  await headline.click();

  const field = page.getByLabel('text', { exact: true });
  await expect(field).toBeVisible();
  // The reveal animation and font loading are still settling right after
  // hydration, and measuring through them would time the page, not the edit.
  await page.waitForTimeout(SETTLE_MS);

  const samples: number[] = [];
  for (let i = 0; i < 12; i++) {
    const started = await page.evaluate(() => performance.now());
    await field.press(String.fromCharCode(97 + (i % 26)));
    // Round-trips to the renderer: resolves only once the browser has
    // committed a frame containing the change, so this includes React's
    // render and the paint, not just the event dispatch.
    const settled = await page.evaluate(
      () =>
        new Promise<number>((resolve) =>
          requestAnimationFrame(() => resolve(performance.now())),
        ),
    );
    samples.push(settled - started);
  }

  samples.sort((a, b) => a - b);
  const p95 = samples[Math.floor(samples.length * 0.95) - 1] ?? 0;
  const median = samples[Math.floor(samples.length / 2)] ?? 0;
  // 100ms is the long-standing threshold below which a response reads as
  // instant rather than as a reaction. The budget is deliberately the
  // perception number and not a tuned-to-current-behaviour one, so this fails
  // when editing stops feeling instant rather than when it merely gets slower.
  expect(p95, `median ${median.toFixed(1)}ms, p95 ${p95.toFixed(1)}ms`).toBeLessThan(100);
});
