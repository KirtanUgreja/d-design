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
  const eyebrow = page.getByText('THE PROBLEM');
  await eyebrow.scrollIntoViewIfNeeded();

  const ltrBox = await eyebrow.boundingBox();
  expect(ltrBox).toBeTruthy();

  await page.getByRole('button', { name: /^dir:/ }).click();
  await eyebrow.scrollIntoViewIfNeeded();
  const rtlBox = await eyebrow.boundingBox();
  expect(rtlBox).toBeTruthy();

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

test('reduced motion collapses reveal to opacity-only, no transform', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/dev/primitives');
  await expect(page.getByRole('button', { name: /^motion:/ })).toHaveText(
    'motion: reduced',
  );

  const headline = page.getByText('Launch with confidence');
  await page.waitForTimeout(300); // past REDUCED_MOTION's 200ms reveal
  const transform = await headline.evaluate((el) => getComputedStyle(el).transform);
  expect(['none', 'matrix(1, 0, 0, 1, 0, 0)']).toContain(transform);
  await expect(headline).toHaveCSS('opacity', '1');
});
