// `/a/{assetId}` — the same-origin asset path the renderer composes.
//
// docs/v2/plan/15-images.md -> "Resolution: a same-origin path, composed from
// an id". `api` already serves the bytes with the right headers; what this adds
// is *origin*. Pointing an `<img>` at `http://localhost:8000/a/…` would work in
// the editor and would mean the published page's CSP has to name a second host,
// which is the one thing that keeps `img-src 'self'` from being available. A
// proxy route costs a hop and buys the strictest image policy there is.
//
// It is deliberately not a redirect. A 302 to the api origin would put that
// origin back in the CSP and defeat the point.

import { NextResponse } from 'next/server';

// The headers `api` sets on the bytes and this route must not lose. Copied
// through explicitly rather than by spreading the upstream response: a
// pass-everything proxy forwards whatever a future upstream adds, and the
// point of this list is that it is the list.
const FORWARDED = [
  'content-type',
  'content-length',
  'cache-control',
  'content-disposition',
  'x-content-type-options',
  'content-security-policy',
] as const;

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { id } = await params;

  const base = process.env.API_URL;
  if (base === undefined || base === '') {
    // Fails closed. A missing upstream is a 404, never a redirect to somewhere
    // a browser might resolve differently.
    return new NextResponse(null, { status: 404 });
  }

  // `id` goes through `encodeURIComponent` and lands on a route typed as
  // `UUID` upstream, so a crafted path is a 422 there rather than a traversal
  // here. Nothing on this side joins it to anything.
  const upstream = await fetch(`${base}/a/${encodeURIComponent(id)}`, {
    cache: 'no-store',
  }).catch(() => null);

  if (upstream === null || !upstream.ok) {
    return new NextResponse(null, { status: 404 });
  }

  const headers = new Headers();
  for (const name of FORWARDED) {
    const value = upstream.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  // Belt and braces: if the upstream ever stopped sending it, the browser must
  // still not sniff. An image reinterpreted as HTML is an XSS.
  headers.set('X-Content-Type-Options', 'nosniff');

  return new NextResponse(upstream.body, { status: 200, headers });
}
