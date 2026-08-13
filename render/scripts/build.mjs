#!/usr/bin/env node
// Build the exporter with esbuild. Bundles render/src + web/src (via the
// @web alias) into one self-contained main.js the CLI can run.
//
// ponytail: esbuild is the bundler (dependencies.md ledger) — JSX transform
// plus alias resolution; a plain ts service cannot do either. The output is a
// single file that imports nothing at runtime except node builtins.
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');

await build({
  entryPoints: [join(root, 'src', 'main.ts')],
  bundle: true,
  platform: 'node',
  format: 'cjs', // react-dom/server uses CJS require() internally; ESM breaks it
  target: 'node20',
  outfile: join(root, 'dist', 'main.cjs'), // .cjs: the package is type:module, CJS needs the extension
  alias: {
    '@web': join(root, '..', 'web', 'src'),
  },
  loader: { '.tsx': 'tsx', '.ts': 'ts', '.css': 'text' },
  logLevel: 'info',
});
