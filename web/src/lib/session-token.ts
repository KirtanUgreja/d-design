/**
 * Web's session-token reader — the server-side path for calling api.
 *
 * web owns the auth tables (Better Auth); api resolves sessions read-only.
 * For web to authenticate to api, it reads its own session's token from the
 * session table (it owns that table) and passes it as `Authorization: Bearer`.
 * api resolves the same token — one trust chain, no shared secret.
 *
 * `import 'server-only'` keeps the token off the client bundle.
 */
import 'server-only';

/**
 * Resolve the current session token from the request's Better Auth cookie.
 *
 * Better Auth signs the cookie as `<token>.<signature>`; api matches the
 * `session.token` column, so the signature must not travel with it. Sending
 * the signed value verbatim made every api call resolve to Unauthorized.
 *
 * Returns null when unauthenticated. There is deliberately no database
 * fallback: "the newest unexpired session for any user" is a permissive
 * default in a credential path (coderules rule 5) — with two users signed in
 * it returns the wrong one. Every caller is request-scoped and already holds
 * a verified session, so the cookie is the only correct source.
 */
export async function getSessionToken(): Promise<string | null> {
  const { cookies } = await import('next/headers');
  const store = await cookies();

  const raw = store.get('better-auth.session_token')?.value;
  if (!raw) {
    return null;
  }

  const token = decodeURIComponent(raw).split('.')[0];
  return token && token.length > 0 ? token : null;
}
