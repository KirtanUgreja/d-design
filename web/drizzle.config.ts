/**
 * Drizzle config for web — the auth tables only (backend.md: web owns
 * exactly seven auth tables; api's Alembic owns everything else and its
 * include_object excludes these). Drizzle-kit pushes/migrates these; the
 * table sets are disjoint and enforced.
 *
 * `drizzle-kit push` creates the tables from web/src/db/schema.ts. `DATABASE_URL`
 * uses the pg driver (Drizzle's node adapter, not asyncpg — that is api's).
 */
import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  dialect: 'postgresql',
  schema: './src/db/schema.ts',
  out: './drizzle',
  dbCredentials: {
    url: process.env.DATABASE_URL ?? 'postgresql://ddesign:ddesign@localhost:5432/ddesign',
  },
});
