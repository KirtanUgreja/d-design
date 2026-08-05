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
 * pages need and app routes must not carry. */
export function appHeaders(): Record<string, string> {
  return {
    'Content-Security-Policy': [
      "default-src 'self'",
      "script-src 'self'",
      "style-src 'self'",
      "img-src 'self' data:",
      "font-src 'self'",
      "frame-ancestors 'none'",
      "base-uri 'none'",
    ].join('; '),
    ...SHARED,
  };
}
