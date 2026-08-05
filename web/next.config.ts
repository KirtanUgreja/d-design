import type { NextConfig } from 'next';

import {
  appHeaders,
  devToolingHeaders,
  embedHeaders,
  publishedHeaders,
} from './src/features/publish/csp';

function asHeaderList(headers: Record<string, string>): { key: string; value: string }[] {
  return Object.entries(headers).map(([key, value]) => ({ key, value }));
}

const nextConfig: NextConfig = {
  // Stable in 16. Hot path #3 is the editor canvas, and the compiler's
  // memoization is worth more there than anywhere else in the product — which
  // is also why the react-hooks lint rules are not optional: a violation
  // silently costs you the memoization rather than failing loudly.
  reactCompiler: true,

  // Reverted in phase 05, having been on since phase 00. Cache Components
  // requires uncached data (the published artifact's fs read) to sit behind
  // a Suspense boundary, and React's streaming SSR reveals a Suspense
  // boundary's content with a client-executed script — meaning that content
  // never appears at all with JS disabled, staying inside its `hidden`
  // wrapper div forever. That directly breaks an explicit, tested exit-gate
  // requirement ("the published page is complete without JavaScript"), and
  // there is no per-route opt-out compatible with the global flag (`export
  // const dynamic = 'force-dynamic'` is rejected outright once this is on).
  // Revisit if a later Next.js version adds one; until then, working without
  // JS outranks an optimization nothing in the codebase depends on yet.
  // cacheComponents: true,

  // The one place all three header sets get attached — csp.ts owns the
  // values, this owns which routes get which (docs/v1/plan/05-publish-present-embed.md).
  //
  // `/dev/*` is excluded from the strict app policy on purpose: the app
  // policy's `style-src` has no `unsafe-inline`, and the renderer is
  // 100%-inline-style by design (patterns.md rule 2 — no Tailwind, no
  // classNames under renderer/). /dev/primitives embeds that renderer
  // directly in an app route to preview it, and so will the editor canvas
  // in phase 09 — applying the strict app CSP there doesn't harden
  // anything (this tooling never ships), it just silently drops every
  // style the renderer sets. Found by the renderer going fontless and
  // black-on-white the first time this file existed.
  // Order is load-bearing: Next merges header sets for every pattern that
  // matches a path, later entries overriding earlier ones for the same key
  // (https://nextjs.org/docs/app/api-reference/config/next-config-js/headers
  // -> "header ordering"). A negative-lookahead catch-all is the documented
  // idiom for Middleware's matcher, not this config's path-to-regexp-based
  // matching, and it silently matched everything here — this app-then-
  // overrides ordering is the version that's actually verified to work.
  async headers() {
    return [
      { source: '/:path*', headers: asHeaderList(appHeaders()) },
      { source: '/p/:id*', headers: asHeaderList(publishedHeaders()) },
      { source: '/e/:id*', headers: asHeaderList(embedHeaders()) },
      // Needs the same `style-src 'unsafe-inline'` relaxation as published
      // pages, for the same reason — an empty override here wouldn't undo
      // the catch-all's CSP, since Next merges per key and there's nothing
      // to merge without an explicit value.
      { source: '/dev/:path*', headers: asHeaderList(publishedHeaders()) },
      // More specific match, applied after — Next's per-key override
      // ordering (see the comment above) means this wins over the
      // catch-all `/dev/:path*` line for every key it sets. Director's
      // harness calls the real API from the browser; `publishedHeaders()`'s
      // `connect-src 'none'` silently blocked every one of those calls
      // (docs/v1/plan/07-director.md, found live) — see csp.ts's
      // `devToolingHeaders` docstring for the second, dev-mode-only break
      // this also fixes.
      { source: '/dev/director/:path*', headers: asHeaderList(devToolingHeaders()) },
    ];
  },
};

export default nextConfig;
