/**
 * The Drizzle client — auth tables only (backend.md).
 *
 * `import 'server-only'` turns a client-component import into a build error
 * (structure.md: the Data Access Layer must never reach a browser).
 */
import 'server-only';

import { drizzle } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';

import * as schema from './schema.js';

const pool = new Pool({
  connectionString:
    process.env.DATABASE_URL ?? 'postgresql://ddesign:ddesign@localhost:5432/ddesign',
});

export const db = drizzle(pool, { schema });

export type DB = typeof db;
