/**
 * Next.js config — the editor app (phase 12).
 *
 * Minimal: no plugins. The pure renderer and design tokens in web/src/features
 * are shared with the render package's esbuild bundling, which is untouched by
 * Next. The editor is a client app wrapping the renderer (patterns.md rule 2).
 *
 * `turbopack.resolveAlias` exists for one reason. tsconfig `paths` maps
 * `next/headers`, `next/navigation` and `next/server` at their `.d.ts` files,
 * because Next ships no `exports` map and `moduleResolution: NodeNext` cannot
 * otherwise resolve those subpaths. Turbopack honours tsconfig `paths` too, so
 * the runtime import resolved to a declaration file with no implementation —
 * `headers()` was `undefined` and every server module 500'd. These aliases
 * point the bundler back at the real CommonJS entry points (the `.d.ts`
 * siblings keep typecheck green).
 */
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: {
    resolveAlias: {
      'next/headers': './node_modules/next/headers.js',
      'next/navigation': './node_modules/next/navigation.js',
      'next/server': './node_modules/next/server.js',
    },
  },
};

export default nextConfig;
