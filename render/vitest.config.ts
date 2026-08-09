import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

// The same `@` -> `web/src` mapping `build.mjs` and `tsconfig.json` use. Three
// declarations of one fact is two too many, and the failure mode of a drifted
// one is a green test suite against a module the bundle does not ship — so if a
// fourth consumer appears, this is the point to hoist it rather than copy it.
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('../web/src', import.meta.url)),
      // The same no-op `server-only` alias `web/vitest.config.ts` and
      // `build.mjs` both carry, for the same reason: outside Next the package
      // is a module that throws on import, and this bundle reaches the
      // art-direction feature's index — which exposes a data module that
      // carries the marker and that nothing here ever calls. `render` holds no
      // credential and therefore no store to read; it takes validated tokens on
      // the wire instead.
      'server-only': fileURLToPath(
        new URL('../web/node_modules/server-only/empty.js', import.meta.url),
      ),
    },
  },
  test: {
    // `server.ts` starts an HTTP listener at import time unless told otherwise,
    // and a test suite that binds a port is a test suite that fails on the
    // second run.
    env: { NODE_ENV: 'test' },
  },
});
