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
  alias: { '@': webSrc },
  // `server-only` is a build-time marker for Next; outside Next it is a module
  // that throws on import. The renderer's data modules are not in this bundle,
  // but anything that transitively touches the marker would be.
  define: { 'process.env.NODE_ENV': '"production"' },
  logLevel: 'info',
});
