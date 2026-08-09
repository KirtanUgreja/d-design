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

// --- The same five, against generated-shaped code ---------------------------
//
// docs/v1/plan/11-visuals-and-slot.md's Verify asks for the phase 04 suite
// re-run against a **generated** slot rather than a fixture, and the reason is
// sharp: `full.json`'s Slot would pass every assertion above even if the
// sandbox did nothing, because it never attempts anything. `/dev/slot` carries
// the code a successful prompt injection would produce — storage, cookies, the
// parent document, a network call, top navigation — so these measure the
// sandbox rather than the politeness of the payload.
//
// `check_slot` (api/features/slot/generate.py) would refuse this code before
// it reached a scene. That it is stopped here *anyway* is the layering the
// whole Slot design rests on: the sandbox is the guarantee, and the check is
// only there so a wasted generation does not ship as a blank frame.

test.describe('Slot sandbox, against generated-shaped code', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dev/slot');
    await page.locator('iframe[title="Hostile generated slot"]').scrollIntoViewIfNeeded();
  });

  test('the hostile slot really does execute — otherwise this proves nothing', async ({
    page,
  }) => {
    // The control on the control. If the payload silently failed to run, every
    // assertion below would pass for the wrong reason.
    await expect(slotFrame(page).locator('#ran')).toHaveText('slot ran');
  });

  test('every escape it attempts is refused', async ({ page }) => {
    const frame = slotFrame(page);
    await expect(frame.locator('#ran')).toBeAttached();
    const escapes = await frame.evaluate(
      () => (window as unknown as { __escapes: Record<string, unknown> }).__escapes,
    );

    // `'threw'` rather than `false`, and the distinction is the finding: in an
    // opaque origin `document.cookie` throws rather than returning an empty
    // string. An unguarded read of it killed the first version of this payload
    // outright, which made the sandbox look perfect for the wrong reason.
    expect(escapes['storage'], 'localStorage should throw').toBe('threw');
    expect(escapes['cookie'], 'document.cookie should throw').toBe('threw');
    expect(escapes['parent'], 'parent.document should throw').toBe('threw');
  });

  test('its network call fails and no request leaves', async ({ page }) => {
    const requests: string[] = [];
    page.on('request', (r) => requests.push(r.url()));
    // A fresh navigation with the listener already attached — `reload()` left
    // `slotFrame` holding the previous document's frame, which is detached by
    // the time anything is evaluated on it.
    await page.goto('/dev/slot');
    await expect(page.locator('iframe[title="Hostile generated slot"]')).toBeAttached();
    await expect.poll(() => slotFrame(page).locator('#ran').count()).toBeGreaterThan(0);
    await page.waitForTimeout(500);
    expect(requests.filter((u) => u.includes('example.com'))).toEqual([]);
  });

  test('its top-navigation attempt does not move the page', async ({ page }) => {
    await expect(slotFrame(page).locator('#ran')).toBeAttached();
    await page.waitForTimeout(300);
    expect(page.url()).toContain('/dev/slot');
  });
});
