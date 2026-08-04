import type { Frame, Page } from '@playwright/test';
import { expect, test } from '@playwright/test';

// security/testing.md -> "Sandbox escape, executed inside a real srcdoc
// iframe, not jsdom." The `full` fixture's scene s8 has the one Slot in the
// tree (docs/v1/scene-schema.md caps an Experience at one). This runs the
// five assertions against that real iframe, not a mock.

function slotFrame(page: Page): Frame {
  const frame = page.frames().find((f) => f !== page.mainFrame());
  if (!frame) throw new Error('Slot iframe not found — did the `full` fixture change?');
  return frame;
}

test.describe('Slot sandbox', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dev/primitives');
    // "full" is the default fixture; confirm rather than assume.
    await expect(page.getByRole('button', { name: 'full', exact: true })).toBeDisabled();
    await page
      .locator('iframe[title="Interactive product demo"]')
      .scrollIntoViewIfNeeded();
  });

  test('localStorage throws inside the sandbox', async ({ page }) => {
    const threw = await slotFrame(page).evaluate(() => {
      try {
        window.localStorage.getItem('x');
        return false;
      } catch {
        return true;
      }
    });
    expect(threw).toBe(true);
  });

  test('document.cookie is unavailable inside the sandbox', async ({ page }) => {
    const result = await slotFrame(page).evaluate(() => {
      try {
        return { threw: false, value: document.cookie };
      } catch {
        return { threw: true, value: '' };
      }
    });
    expect(result.threw || result.value === '').toBe(true);
  });

  test('parent.document throws inside the sandbox', async ({ page }) => {
    const threw = await slotFrame(page).evaluate(() => {
      try {
        // eslint-disable-next-line @typescript-eslint/no-unused-expressions
        window.parent.document;
        return false;
      } catch {
        return true;
      }
    });
    expect(threw).toBe(true);
  });

  test('fetch to any origin fails inside the sandbox', async ({ page }) => {
    const failed = await slotFrame(page).evaluate(async () => {
      try {
        await fetch('https://example.com');
        return false;
      } catch {
        return true;
      }
    });
    expect(failed).toBe(true);
  });

  test('top navigation from the sandbox does not occur', async ({ page }) => {
    const urlBefore = page.url();
    await slotFrame(page).evaluate(() => {
      try {
        const top = window.top;
        if (top) top.location.href = 'https://example.com';
      } catch {
        // Expected: an opaque-origin frame cannot reach `window.top`'s location.
      }
    });
    await page.waitForTimeout(200);
    expect(page.url()).toBe(urlBefore);
  });
});
