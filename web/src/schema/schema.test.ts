import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { experienceSchema } from './index';

// The other half of the cross-language agreement test. The Python half is
// api/tests/test_schema_codegen.py, and both read the same fixture files.
//
// Only the wire-representable invalid cases live here — the ones JSON Schema
// can express as a field's shape (a length cap, an item count, a pattern).
// The other nine of the fourteen rejection rules need to count, order, or
// cross-reference across sibling fields or nested arrays ("exactly one hook
// and it is first", "at least one CTA somewhere", "ids unique across this
// list") — JSON Schema validates one node's shape and has no vocabulary for a
// predicate over a whole tree. Those nine are Python-only and asserted in
// api/schema/test_scene.py against the full fourteen in invalid_cases.json.
type Case = { name: string; valid: boolean; data: unknown };

const FIXTURES = join(import.meta.dirname, '..', '..', '..', 'api', 'schema', 'fixtures');
const readJson = (name: string): unknown =>
  JSON.parse(readFileSync(join(FIXTURES, name), 'utf8'));

const VALID_FIXTURES = ['minimal', 'full', 'hostile'];

const cases: Case[] = [
  ...VALID_FIXTURES.map((name) => ({
    name,
    valid: true,
    data: readJson(`${name}.json`),
  })),
  ...(readJson('wire_invalid_cases.json') as Case[]),
];

describe('generated Zod validator agrees with Pydantic', () => {
  it('has fixtures to check', () => {
    expect(cases.length).toBe(VALID_FIXTURES.length + 5);
  });

  for (const c of cases) {
    it(`${c.valid ? 'accepts' : 'rejects'}: ${c.name}`, () => {
      expect(experienceSchema.safeParse(c.data).success).toBe(c.valid);
    });
  }
});
