// One Chromium, reused across requests.
//
// Launching a browser per screenshot is the difference between the visual
// verification loop in phase 09 costing latency and costing a minute — a launch
// is roughly a second, a page is roughly ten milliseconds. So the browser is a
// singleton and the *page* is what is created and closed per request.
//
// A page per request rather than a pooled page, deliberately: a reused page
// carries the last render's scroll position, its fonts, its custom properties
// and anything a `Slot` iframe did to it. Pooling those would trade a
// negligible cost for a class of "the screenshot has the previous scene in it"
// bug that is invisible until someone looks at a hundred of them.

import { chromium, type Browser, type Page } from 'playwright';

let browser: Browser | null = null;
let launching: Promise<Browser> | null = null;

/** Concurrent first calls must not each launch a browser, so the *promise* is
 * memoized rather than the result — two requests arriving before the first
 * launch resolves would otherwise leave one Chromium orphaned with nothing
 * holding a reference to close it. */
export async function getBrowser(): Promise<Browser> {
  if (browser !== null && browser.isConnected()) return browser;
  launching ??= chromium
    .launch({
      // Never `--no-sandbox`. The Dockerfile runs this as a non-root user in
      // an image that ships the sandbox helper, and a container that silently
      // fell back would look identical from the outside
      // (docs/security/testing.md -> "Chromium runs sandboxed").
      args: ['--disable-dev-shm-usage'],
    })
    .then((b) => {
      browser = b;
      launching = null;
      return b;
    });
  return launching;
}

export async function withPage<T>(
  viewport: { width: number; height: number },
  fn: (page: Page) => Promise<T>,
): Promise<T> {
  const context = await (await getBrowser()).newContext({ viewport });
  try {
    return await fn(await context.newPage());
  } finally {
    // A context, not just a page: closing the context is what actually
    // releases storage, service workers and any frame the page opened.
    await context.close();
  }
}

export async function closeBrowser(): Promise<void> {
  await browser?.close();
  browser = null;
}
