import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

// Mirrors tsconfig.json's "@/*": ["./src/*"]. A few lines of our own rather
// than a plugin dependency for a one-entry alias map.
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // e2e/ is Playwright's tree, not Vitest's — the two share the `.spec`
    // naming space and Vitest's default include glob would otherwise pick
    // them up and fail on Playwright's `test()`/`test.describe()`.
    exclude: ['node_modules/**', 'e2e/**'],
  },
});
