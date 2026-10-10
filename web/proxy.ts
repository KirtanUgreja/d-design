// Next 16's request proxy (the file once called middleware.ts). An optimistic
// check only: a session cookie is present, or the visitor goes to sign-in with
// a return path. It never grants anything — the account and deck pages check
// the session for real on the server, and the /api proxy refuses without one
// (CVE-2025-29927: authorization never lives in middleware alone).
import { getSessionCookie } from "better-auth/cookies";
import { NextResponse, type NextRequest } from "next/server";

export function proxy(request: NextRequest): NextResponse {
  if (getSessionCookie(request)) return NextResponse.next();
  const to = new URL("/sign-in", request.url);
  to.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(to);
}

// The app routes. Public on purpose: the composer at / (a brief typed there
// waits through sign-up, A5), sign-in and sign-up.
export const config = {
  matcher: ["/d/:path*", "/account/:path*", "/decks/:path*"],
};
