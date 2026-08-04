import { defineConfig } from '@playwright/test';

// The security assertions that need a real browser (docs/coderules/dependencies.md
// -> Playwright's baseline entry), starting with phase 04's Slot sandbox and
// RTL-mirror checks.
//
// Runs against a production build (`next start`), not `next dev`. Turbopack
// dev's on-demand first compile plus Fast Refresh detaches and remounts DOM
// nodes shortly after first paint — invisible by eye, but exactly the window
// `scrollIntoViewIfNeeded` and `boundingBox` run in, and it flaked the
// RTL-mirror test on every cold CI start. `next build && next start` costs a
// slower first run locally and is also the more honest target: it's what a
// published page's HTML/hydration timing actually looks like.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3100',
  },
  webServer: {
    command: 'pnpm build && pnpm exec next start --port 3100',
    url: 'http://localhost:3100',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
