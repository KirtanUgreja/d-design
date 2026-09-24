/**
 * Drizzle config for web — the auth tables only (backend.md: web owns
 * exactly seven auth tables; api's Alembic owns everything else and its
 * include_object excludes these). Drizzle-kit pushes/migrates these; the
 * table sets are disjoint and enforced.
 *
 * `drizzle-kit push` creates the tables from web/src/db/schema.ts. `DATABASE_URL`
 * uses the pg driver (Drizzle's node adapter, not asyncpg — that is api's).
 *
 * `schemaFilter` keeps a push inside the `auth` schema. Without it, drizzle-kit
 * sees api's public tables as unmanaged drift and prompts to drop them — the
 * disjoint-ownership rule becomes a prompt rather than a fact.
 */
import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  dialect: 'postgresql',
  schema: './src/db/schema.ts',
  out: './drizzle',
  schemaFilter: ['auth'],
  dbCredentials: {
    url: process.env.DATABASE_URL ?? 'postgresql://ddesign:ddesign@localhost:5432/ddesign',
  },
});
