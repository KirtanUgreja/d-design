/**
 * Better Auth — the auth library in Node (v3, phase 16).
 *
 * backend.md: Better Auth stays in Node with users in our own Postgres (that
 * real FK between user and data is what makes the session-variable RLS work).
 * The Drizzle adapter owns the seven auth tables; api resolves sessions
 * read-only via the same database.
 *
 * Signup, login and reset are enumeration-safe (same response for existing
 * and non-existing addresses) — tenancy-and-data.md.
 */
import { betterAuth } from 'better-auth';
import { drizzleAdapter } from 'better-auth/adapters/drizzle';

import { db } from '../db/index.js';
import * as schema from '../db/schema.js';

export const auth = betterAuth({
  database: drizzleAdapter(db, {
    provider: 'pg',
    schema: {
      user: schema.user,
      session: schema.session,
      account: schema.account,
      verification: schema.verification,
    },
  }),
  // The secret and base URL come from env (fail closed: no default secret is
  // ever a permissive fallback in the credential path). Set them in .env —
  // .env.example documents them.
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: process.env.BETTER_AUTH_URL,
  emailAndPassword: {
    enabled: true,
    // Enumeration safety: a failed signup/login returns the same error for
    // existing and non-existing addresses.
    minPasswordLength: 8,
  },
  // OAuth providers are configured via env when their keys exist; the phase's
  // deterministic gate tests email auth.
  socialProviders: {},
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
  },
  advanced: {
    database: {
      // Ids must be UUIDs. Better Auth's default is a 32-char nanoid, but
      // every user-referencing column api owns is `uuid` (quotas.account_id,
      // experiences.owner_id, teams.owner_id, team_members.user_id). A nanoid
      // id failed at the first write with `invalid input for query argument`
      // — invisible until now because the seeded test user was a UUID.
      generateId: () => globalThis.crypto.randomUUID(),
    },
  },
});
