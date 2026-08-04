import { defineConfig } from '@playwright/test';

// The security assertions that need a real browser (docs/coderules/dependencies.md
// -> Playwright's baseline entry), starting with phase 04's Slot sandbox and
// RTL-mirror checks. Reuses the same dev server the rest of the app runs —
// no separate build step for e2e.
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
    command: 'pnpm dev --port 3100',
    url: 'http://localhost:3100',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
