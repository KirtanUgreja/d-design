import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

// Mirrors tsconfig.json's "@/*": ["./src/*"]. A few lines of our own rather
// than a plugin dependency for a one-entry alias map.
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      // Next's bundler sets the `react-server` export condition, which
      // resolves this package to its no-op branch; Vitest doesn't set that
      // condition (and setting it globally would also flip React itself to
      // its server-components-only build, breaking every hook-using test).
      // Aliasing just this one specifier gets the same no-op without that.
      'server-only': fileURLToPath(
        new URL('./node_modules/server-only/empty.js', import.meta.url),
      ),
    },
  },
  test: {
    // e2e/ is Playwright's tree, not Vitest's — the two share the `.spec`
    // naming space and Vitest's default include glob would otherwise pick
    // them up and fail on Playwright's `test()`/`test.describe()`.
    exclude: ['node_modules/**', 'e2e/**'],
    // publish.test.ts mocks fetch, so this is never dialed — it only needs
    // to exist so publish.ts's required-env check doesn't fail the test run.
    env: { API_URL: 'http://localhost:8000' },
  },
});
