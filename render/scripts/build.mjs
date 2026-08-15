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

// The CLI (main.ts): bundles Playwright for the PDF path. Built separately
// from the server so the CVE-rich dependency never enters the render service
// bundle (backend.md trust split).
await build({
  entryPoints: [join(root, 'src', 'main.ts')],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  target: 'node20',
  outfile: join(root, 'dist', 'main.cjs'),
  external: ['playwright', 'playwright-core'],
  alias: {
    '@web': join(root, '..', 'web', 'src'),
  },
  loader: { '.tsx': 'tsx', '.ts': 'ts', '.css': 'text' },
  logLevel: 'info',
});

// The server (server.ts): the render-as-a-service entry (phase 18). Same
// exporter, no Playwright, no top-level await — a tiny HTTP endpoint web
// calls at publish time. Its bundle carries no credential, no model key.
await build({
  entryPoints: [join(root, 'src', 'server.ts')],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  target: 'node20',
  outfile: join(root, 'dist', 'server.cjs'),
  alias: {
    '@web': join(root, '..', 'web', 'src'),
  },
  loader: { '.tsx': 'tsx', '.ts': 'ts', '.css': 'text' },
  logLevel: 'info',
});
