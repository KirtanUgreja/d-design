// An asset id becomes a URL. String work, deliberately.
//
// This is the file that closes v1's longest-standing `ponytail:` — `Image`
// blocks carried an `assetId` and nothing resolved it, so every image in the
// product was a grey rectangle (docs/v2/plan/15-images.md).
//
// **The renderer is pure and cannot fetch** (patterns.md rule 6), so the URL
// has to be *derivable* rather than looked up, which is exactly what v1
// recorded as the blocker. Composing a path from an id behaves identically in
// the browser, the app server and the render service. A signed URL would not:
// it needs a secret, a clock and a network call, and it would put all three
// inside the renderer.
//
// Same-origin, which is the decision v1 flagged and left open. Taking it buys
// `img-src 'self'` on the published page, no third-party image host, no CORS,
// and a cache story that is one header. The route is
// `web/src/app/a/[id]/route.ts`; the authorization is on it, not here.

/** `encodeURIComponent`, even though ids are UUIDs. The id reaches here from a
 * parsed scene tree, and a schema is a contract rather than a guarantee about
 * every future caller — encoding costs nothing and means a crafted id lands on
 * the route as a 404 instead of anywhere else. */
export function assetUrl(assetId: string): string {
  return `/a/${encodeURIComponent(assetId)}`;
}
