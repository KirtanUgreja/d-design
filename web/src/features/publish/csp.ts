// The header sets, one place (docs/v1/plan/05-publish-present-embed.md ->
// "CSP"). `next.config.ts`'s `headers()` is what actually attaches these to
// a response; this file only owns what the values are, so the three sets
// can never drift between wherever they're read.

const SHARED = {
  'Referrer-Policy': 'no-referrer',
  'X-Content-Type-Options': 'nosniff',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
};

/** `connect-src 'none'` genuinely holds in v1 — the two endpoints that
 * weaken it (personalization fields, the analytics beacon) are v3. Write
 * the assertion as zero now; the diff when v3 adds two is the point.
 *
 * `script-src` carries `'unsafe-inline'` too, and that one is not in the
 * plan doc's original list — found live, not designed in. `/p/[id]` needs a
 * Suspense boundary to satisfy Cache Components (the artifact read is
 * per-request, uncached data), and React's streaming SSR reveals that
 * boundary's content with a framework-generated inline `<script>` — without
 * `unsafe-inline` the reveal script is blocked and the content sits inside
 * its `hidden` wrapper div forever. The correct tightening is a per-request
 * nonce threaded through middleware (Next's documented pattern); this is
 * the v1 answer given Cache Components' streaming requirement, not the
 * intended end state. */
export function publishedHeaders(): Record<string, string> {
  return {
    'Content-Security-Policy': [
      "default-src 'none'",
      "script-src 'self' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data:",
      "font-src 'self'",
      "connect-src 'none'",
      'frame-ancestors *',
      "base-uri 'none'",
      "form-action 'none'",
    ].join('; '),
    ...SHARED,
  };
}

/** Same artifact, same renderer, no second code path — `frame-ancestors *`
 * on the published set already permits arbitrary embedding, so there is
 * nothing v1 needs stricter or looser here. Kept as its own named export
 * (rather than importing `publishedHeaders` at each embed call site) so a
 * real divergence later — a scoped allow-list, different caching — is a
 * change to one function instead of a search-and-replace. */
export function embedHeaders(): Record<string, string> {
  return publishedHeaders();
}

/** App routes: no framing, no inline styles — the two allowances published
 * pages need and app routes must not carry.
 *
 * **`connect-src` is explicit, and it has to be.** `api` is a different
 * origin from `web`, and the pipeline's browser-side calls — Intake's
 * interview, Director, and Build's SSE stream — all run from an app route
 * (`/new`). Without this line `connect-src` falls back to `default-src
 * 'self'` and every one of them is blocked, in production as well as in dev.
 * Until phase 08 every such call lived under `/dev/*`, which is why
 * `devToolingHeaders` below found the same break first and this one did not:
 * the app CSP had never had a browser-to-api call to allow. The allowance is
 * one exact origin from configuration, not a wildcard.
 *
 * **`unsafe-eval` in development only.** `next dev`'s React needs it to
 * hydrate at all; a production build does not, which is why `pnpm test:e2e`
 * (which runs against `pnpm build`) never sees this and a `pnpm dev` session
 * sees nothing but dead buttons. Gated on `NODE_ENV` so the shipped policy
 * stays strict — the same break `devToolingHeaders` documents, reaching a
 * real product route for the first time rather than a harness. */
export function appHeaders(): Record<string, string> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
  const script =
    process.env.NODE_ENV === 'production'
      ? "script-src 'self' 'unsafe-inline'"
      : "script-src 'self' 'unsafe-inline' 'unsafe-eval'";
  return {
    'Content-Security-Policy': [
      "default-src 'self'",
      script,
      "style-src 'self'",
      // The api origin, because that is where uploaded assets are served
      // from — `api` owns object storage and there is exactly one storage
      // path (docs/v1/plan/10-brand-and-uploads.md). One exact origin from
      // configuration, not a wildcard, and it stays out of `publishedHeaders`:
      // a published page still reaches nothing.
      `img-src 'self' data: ${apiUrl}`.trim(),
      "font-src 'self'",
      `connect-src 'self' ${apiUrl}`.trim(),
      "frame-ancestors 'none'",
      "base-uri 'none'",
    ].join('; '),
    ...SHARED,
  };
}

/** App routes that embed the renderer — the editor canvas, and any preview
 * that follows it.
 *
 * The renderer is 100%-inline-style by design (docs/coderules/patterns.md rule
 * 2 — no Tailwind, no classNames under `renderer/`), so `appHeaders`'s
 * `style-src 'self'` silently drops every style it sets and the page renders
 * fontless and unstyled. That failure is already written down twice in this
 * codebase — it is why `/dev/primitives` runs on `publishedHeaders`, and
 * `next.config.ts` records finding it the first time — and the editor is the
 * first *product* route to embed the renderer, so it is the first to need the
 * same allowance without being dev tooling.
 *
 * Everything else stays at the app policy: `frame-ancestors 'none'` (an
 * editor in an iframe is a clickjacking target in a way a published page is
 * not), and `connect-src` limited to the one API origin. */
export function editorHeaders(): Record<string, string> {
  const app = appHeaders();
  const policy = app['Content-Security-Policy'] ?? '';
  return {
    ...app,
    'Content-Security-Policy': policy.replace(
      "style-src 'self'",
      "style-src 'self' 'unsafe-inline'",
    ),
  };
}

/** `/dev/*` pages that call the real API in the browser — found live,
 * building the Director harness (docs/v1/plan/07-director.md): every
 * button on the page silently did nothing under `publishedHeaders()`.
 * Two separate breaks, not one — `connect-src 'none'` blocks the fetch to
 * `api` regardless of dev or production mode, and `next dev`'s React
 * additionally needs `unsafe-eval` to hydrate at all (a production build
 * does not; this is why `pnpm test:e2e`, which runs against `pnpm build`,
 * never hit it). `/dev/primitives` never needed this — it reads fixtures
 * server-side and makes zero client-side network calls — so it stays on
 * `publishedHeaders()`; a harness that exercises a live feature needs
 * this instead. Same "this tooling never ships" reasoning as every other
 * `/dev/*` relaxation: no real user ever reaches this route. */
export function devToolingHeaders(): Record<string, string> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
  return {
    'Content-Security-Policy': [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      // The api origin serves uploaded assets, and `/dev/visuals` reviews the
      // five generators *over a real photograph* — without this the photo half
      // of that page is a black rectangle that looks like a passing review.
      `img-src 'self' data: ${apiUrl}`.trim(),
      "font-src 'self'",
      `connect-src 'self' ${apiUrl}`.trim(),
      "frame-ancestors 'none'",
      "base-uri 'none'",
    ].join('; '),
    ...SHARED,
  };
}
