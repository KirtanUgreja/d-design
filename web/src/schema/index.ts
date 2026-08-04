// The public surface of the schema. Hand-written; everything it re-exports is
// generated from api/schema/*.py and lives under ./generated, which nothing
// outside this file should import.
//
// ponytail: this folder has the layout a package would have. When `render`
// arrives in v2 there is a second TypeScript consumer, and publishing it as
// @d-design/schema is a package.json and a Changeset.

export { probeSchema, type Probe } from './generated/schema';
