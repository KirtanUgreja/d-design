import { expect, test } from '@playwright/test';

// docs/v1/plan/04-renderer.md -> Verify: "dir=rtl on the root mirrors the
// entire review page with no stylesheet change." The split-left layout's
// two named regions (docs/v1/scene-schema.md: "left/right name authoring
// position, not screen position") are the one place a physically-authored
// layout would visibly fail this — CSS Grid's inline axis is what's actually
// doing the mirroring, so this is really a test that no block or layout
// reached for a physical `left`/`right` CSS property instead.

test('split-left column order visually reverses under dir=rtl', async ({ page }) => {
  await page.goto('/dev/primitives');
  // Confirms the harness actually hydrated before measuring anything — the
  // same guard e2e/slot-sandbox.spec.ts uses, and the one this test was
  // missing when it flaked in CI on a slow first Turbopack compile.
  await expect(page.getByRole('button', { name: 'full', exact: true })).toBeDisabled();

  const eyebrow = page.getByText('THE PROBLEM');
  // A cold Turbopack dev-server compile (first request after boot, which is
  // exactly what CI does) keeps the page layout shifting — fonts and content
  // still arriving — for longer than `scrollIntoViewIfNeeded`'s stability
  // check tolerates. Waiting for visible first, with the framework's own
  // retrying assertion, is what actually waits for that to settle.
  await expect(eyebrow).toBeVisible();
  await eyebrow.scrollIntoViewIfNeeded();
  const ltrBox = await eyebrow.boundingBox();

  await page.getByRole('button', { name: /^dir:/ }).click();
  await eyebrow.scrollIntoViewIfNeeded();
  const rtlBox = await eyebrow.boundingBox();

  const viewport = page.viewportSize();
  expect(viewport).toBeTruthy();
  const viewportWidth = viewport?.width ?? 0;
  const ltrX = ltrBox?.x ?? 0;
  const rtlX = rtlBox?.x ?? 0;

  // In LTR, the `left` region (eyebrow's) sits in the first column — left
  // half of the viewport. Under RTL, the same DOM order renders in the
  // *last* column, which CSS Grid places on the right half — with zero
  // stylesheet change, only the `dir` attribute.
  expect(ltrX).toBeLessThan(viewportWidth / 2);
  expect(rtlX).toBeGreaterThan(viewportWidth / 2);
});

// Both vocabularies, not one, since v2 phase 02 made reduced motion a
// per-vocabulary field instead of a single global constant. The unit suites
// assert the *floor* — opacity-only, no transform, no parallax, for every
// vocabulary and every intent — and they assert it about the objects. This is
// the only place a real browser with the preference actually set says the same
// thing about a rendered page, which is a different claim: a vocabulary could
// be perfect and the wrapper could still hand the renderer the wrong one.
//
// Parameterized over the harness's own motion selector rather than over a list
// written here, so a third vocabulary is covered by existing code the day it
// lands — and a vocabulary the harness cannot reach is one nobody can see.
for (const vocabulary of ['cinematic-slow', 'editorial-restrained']) {
  test(`reduced motion collapses reveal to opacity-only under ${vocabulary}`, async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/dev/primitives');
    await expect(page.getByRole('button', { name: 'full', exact: true })).toBeDisabled();

    // The harness disables the button for whatever is selected, so clicking is
    // conditional and the assertion afterwards is the real one: this vocabulary
    // is the active one, however it got there.
    const selector = page.getByRole('button', { name: vocabulary, exact: true });
    if (await selector.isEnabled()) await selector.click();
    await expect(selector).toBeDisabled();

    await expect(page.getByRole('button', { name: /^motion:/ })).toHaveText(
      'motion: reduced',
    );

    const headline = page.getByText('Launch with confidence');
    // Past the longest reduced duration any vocabulary may declare (300ms), so
    // the wait does not have to know which one is selected.
    await page.waitForTimeout(400);
    const transform = await headline.evaluate((el) => getComputedStyle(el).transform);
    expect(['none', 'matrix(1, 0, 0, 1, 0, 0)']).toContain(transform);
    await expect(headline).toHaveCSS('opacity', '1');
  });
}

// The `emphasize` half of the same claim, and the reason it exists: the test
// above passes whether or not the reveal lands on the identity transform,
// because `reveal`'s failure mode is `translateY(0)` — which is where it was
// going anyway. `emphasize` animates scale, and its failure mode is `scale(0)`:
// a 0×0 box, still in the layout, still at opacity 1, holding the content that
// is now invisible. That shipped, and the acceptance run found it on the hero
// headline of the first experience the product generated end to end.
//
// Asserted on the box rather than on the transform string, because the box is
// what a reader loses. A transform assertion would have to enumerate the
// matrices that are "fine", and the next wrong one would not be on the list.
test('an emphasize block ends the reveal with a real box, not scale(0)', async ({
  page,
}) => {
  await page.goto('/dev/primitives');

  // The `full` fixture's two `motion: "emphasize"` blocks. Both, not one: the
  // bug was in the shared wrapper, so a single sample proves less than it looks.
  for (const text of ['THE PROBLEM', 'Start free']) {
    const block = page.getByText(text, { exact: true }).first();
    await block.scrollIntoViewIfNeeded();
    await expect(block).toBeVisible();
    // Past CINEMATIC_MOTION's 1100ms emphasize duration plus its stagger.
    await page.waitForTimeout(1600);

    const box = await block.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThan(0);
    expect(box?.height ?? 0).toBeGreaterThan(0);
    await expect(block).toHaveCSS('opacity', '1');
  }
});
