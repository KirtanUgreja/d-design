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

import { gt } from 'drizzle-orm';

import { db } from '../db/index.js';
import { session } from '../db/schema.js';

/**
 * Resolve the current session token. Uses the Better Auth session cookie if
 * present; otherwise falls back to reading the session table for the newest
 * unexpired session (local/dev convenience). Returns null when unauthenticated.
 */
export async function getSessionToken(): Promise<string | null> {
  const { cookies } = await import('next/headers');
  const store = await cookies();
  // Better Auth's cookie name (session token for the default plugin).
  const cookieToken = store.get('better-auth.session_token')?.value;
  if (cookieToken) {
    return cookieToken;
  }

  // Fallback: the newest unexpired session row. This is the local/dev path —
  // the cookie is the real mechanism in production.
  const rows = await db
    .select({ token: session.token })
    .from(session)
    .where(gt(session.expiresAt, new Date()))
    .orderBy(session.createdAt)
    .limit(1);
  return rows[0]?.token ?? null;
}
