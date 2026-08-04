import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { probeSchema } from './index';

// The other half of the cross-language agreement test. The Python half is
// api/tests/test_schema_codegen.py, and both read this one file. Two
// validators, one fixture set, one verdict per case — a codegen bug shows up
// as the two halves disagreeing, which is what would actually catch it.
type Case = { name: string; valid: boolean; data: unknown };

const cases = JSON.parse(
  readFileSync(
    join(
      import.meta.dirname,
      '..',
      '..',
      '..',
      'api',
      'tests',
      'fixtures',
      'probe_cases.json',
    ),
    'utf8',
  ),
) as Case[];

describe('generated Zod validator agrees with Pydantic', () => {
  it('has fixtures to check', () => {
    expect(cases.length).toBeGreaterThan(0);
  });

  for (const c of cases) {
    it(`${c.valid ? 'accepts' : 'rejects'}: ${c.name}`, () => {
      expect(probeSchema.safeParse(c.data).success).toBe(c.valid);
    });
  }
});
