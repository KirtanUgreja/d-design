// One bundle, produced by esbuild.
//
// The alternative was running TypeScript directly: Node 26 strips types
// natively, so a plain `.ts` service would need no build at all. It does not
// transform **JSX**, and the renderer is entirely `.tsx` — so a compiler is
// unavoidable. `docs/coderules/dependencies.md` draws the line at "who gets
// hurt if I get it subtly wrong", and a JSX/TS compiler is squarely on the
// don't-write-your-own side of it.
//
// Bundling also resolves `@/` against `web/src`, which is what lets this
// service import the renderer rather than copy it.

import { build } from 'esbuild';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const webSrc = fileURLToPath(new URL('../web/src', import.meta.url));

await build({
  entryPoints: ['src/server.ts'],
  outfile: 'dist/server.js',
  bundle: true,
  platform: 'node',
  format: 'esm',
  target: 'node22',
  jsx: 'automatic',
  sourcemap: true,
  // Playwright ships platform binaries and resolves browsers relative to its
  // own install path; bundling it would break both. React stays external for
  // the ordinary reason — one copy, resolved by Node.
  external: ['playwright', 'react', 'react-dom', 'react-dom/server'],
  alias: {
    '@': webSrc,
    // `server-only` is a build-time marker for Next; outside Next it is a
    // module that *throws on import*, and the package ships `empty.js` for
    // exactly the environment this is — its own export map resolves to that
    // file under the `react-server` condition.
    //
    // It became load-bearing in v2 phase 01. `art-direction.data.ts` reads the
    // art-direction store and carries the marker like every other data module,
    // and this bundle reaches the feature's index to get `fromRecord` and
    // `toCssVars`. The marker's job is to stop a *client bundle* importing a
    // data module; this service has no client bundle, and the module it guards
    // is never called here — `render` receives validated tokens on the wire
    // precisely because it holds no credential to read a store with.
    'server-only': join(webSrc, '..', 'node_modules', 'server-only', 'empty.js'),
  },
  define: { 'process.env.NODE_ENV': '"production"' },
  logLevel: 'info',
});
