import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

// render bundles web/src (the pure renderer + design tokens) via esbuild; the
// alias keeps tests resolving the same source tree the exporter will bundle.
export default defineConfig({
  resolve: {
    alias: {
      '@web': fileURLToPath(new URL('../web/src', import.meta.url)),
    },
  },
  test: {
    include: ['tests/**/*.test.ts', 'tests/**/*.test.tsx'],
  },
});
