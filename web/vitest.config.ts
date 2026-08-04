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
});
