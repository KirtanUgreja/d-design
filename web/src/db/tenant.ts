/**
 * The tenant transaction wrapper — the only place app.user_id is set in
 * TypeScript (patterns.md rule 4).
 *
 * Exactly two wrappers, one per language; this is the TypeScript one (the
 * Python one is api/db/tenant.py). The `true` in set_config scopes the value
 * to the transaction, so a pooled connection never serves the previous user.
 *
 * This wrapper deliberately does NOT `set local role app_user`, though api's
 * does. The role switch is what makes RLS apply (a superuser bypasses it), but
 * web reads only the auth tables — which web owns and `app_user` has no grants
 * on — so switching here would turn every session lookup into "permission
 * denied". If web ever reads an app table, that table needs the role switch
 * and a grant, together.
 *
 * `import 'server-only'` keeps it off the client bundle.
 */
import 'server-only';

import { sql, type ExtractTablesWithRelations } from 'drizzle-orm';
import type { PgTransaction } from 'drizzle-orm/pg-core';
import type { NodePgQueryResultHKT } from 'drizzle-orm/node-postgres';

import { db } from './index.js';
import * as schema from './schema.js';

/** The transaction asUser hands to its callback — what db.transaction gives. */
export type Tx = PgTransaction<
  NodePgQueryResultHKT,
  typeof schema,
  ExtractTablesWithRelations<typeof schema>
>;

export function asUser<T>(userId: string, fn: (tx: Tx) => Promise<T>): Promise<T> {
  return db.transaction(async (tx) => {
    await tx.execute(sql`select set_config('app.user_id', ${userId}, true)`);
    return fn(tx);
  });
}
