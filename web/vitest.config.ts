import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  resolve: {
    alias: {
      '@web': fileURLToPath(new URL('./src', import.meta.url)),
      // server-only is a Next.js build marker; vitest has no bundler, so the
      // real module (which throws outside Next) is swapped for a no-op.
      'server-only': fileURLToPath(new URL('./tests/mocks/server-only.js', import.meta.url)),
    },
  },
  test: {
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    environment: 'node',
  },
});
