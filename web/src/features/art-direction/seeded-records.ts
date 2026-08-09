// The seeded art directions, read off disk. **Dev harnesses and tests only.**
//
// `api/schema/fixtures/art_directions.json` is generated from
// `api/features/art_direction/seed.py` — the same module migration 0011 seeds
// the database from — and `api/tests/test_art_direction_seed.py` fails if the
// two disagree. So this is not a second source of truth; it is the same one,
// reachable without a database.
//
// **It is not a fallback and must never become one.** A production path that
// quietly rendered these when `api` was unreachable would serve a stale art
// direction to a customer's audience and report success — the exact shape of
// failure `docs/coderules/README.md` rule 10 is about. Production reads the
// store (`art-direction.data.ts`) and fails closed.
//
// Two callers, both of which are honest ones: the `/dev/*` harnesses, which
// exist to look at tokens with nothing else running, and the tests that assert
// this format renders what v1 rendered.
//
// `node:fs` rather than a JSON import: it makes a client component importing
// this a build error, which is the same marker `server-only` would be without
// pulling the throwing module into `render`'s bundle.

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import {
  artDirectionRecordSchema,
  motionVocabularyRecordSchema,
  type ArtDirectionRecord,
  type MotionVocabularyRecord,
} from '@/schema';

import { fromMotionRecord } from './from-motion-record';
import { fromRecord, type ResolvedRecord } from './from-record';
import type { MotionVocabulary } from './motion-vocabulary';

// `process.cwd()` is `web/` under `next dev`, `next build` and Vitest alike —
// `import.meta.dirname` is not populated in Turbopack's SSR bundle, which
// `src/app/dev/primitives/page.tsx` already found the hard way.
const FIXTURES = join(process.cwd(), '..', 'api', 'schema', 'fixtures');
const FIXTURE = join(FIXTURES, 'art_directions.json');
const MOTION_FIXTURE = join(FIXTURES, 'motion_vocabularies.json');

/** Parsed, not cast. The fixture crosses a language boundary, so it gets the
 * same one parse at entry that the API response does — and a fixture that
 * stopped matching the schema should fail here rather than three frames
 * later. */
export function seededRecords(): ArtDirectionRecord[] {
  return artDirectionRecordSchema
    .array()
    .parse(JSON.parse(readFileSync(FIXTURE, 'utf8')));
}

/** One seeded art direction by id, for the callers that name one — the
 * fixtures, the tests, and the dev harnesses that show two side by side. */
export function seededRecord(id: string): ArtDirectionRecord {
  const found = seededRecords().find((record) => record.id === id);
  if (found === undefined) throw new Error(`seeded-records: no art direction ${id}`);
  return found;
}

/** A seeded art direction, resolved to the two objects the renderer takes.
 *
 * Throws rather than returning a `Result`, and the split is rule 3's: a record
 * fetched from the store failing to resolve is an expected state of two
 * services deployed separately, but a *checked-in fixture* failing to resolve
 * is a bug in this repository — and one `api/tests/test_art_direction_seed.py`
 * would already have caught. A `Result` here would only ever be unwrapped. */
export function seededArtDirection(id: string): ResolvedRecord {
  const result = fromRecord(seededRecord(id));
  if (!result.ok) throw new Error(`seeded-records: ${id}: ${result.error.message}`);
  return result.value;
}

/** Every seeded art direction, resolved. What the dev harnesses that offer all
 * of them iterate. */
export function seededArtDirections(): ResolvedRecord[] {
  return seededRecords().map((record) => seededArtDirection(record.id));
}

// ---------------------------------------------------------------------------
// Motion, the other axis. Same arrangement, same warning: not a fallback.
// ---------------------------------------------------------------------------

export function seededMotionRecords(): MotionVocabularyRecord[] {
  return motionVocabularyRecordSchema
    .array()
    .parse(JSON.parse(readFileSync(MOTION_FIXTURE, 'utf8')));
}

export function seededMotionRecord(id: string): MotionVocabularyRecord {
  const found = seededMotionRecords().find((record) => record.id === id);
  if (found === undefined) throw new Error(`seeded-records: no motion vocabulary ${id}`);
  return found;
}

/** A seeded vocabulary, resolved to the two the wrapper chooses between.
 *
 * Throws rather than returning a `Result`, for the reason `seededArtDirection`
 * does: a checked-in fixture that will not resolve is a bug in this repository
 * and one `api/tests/test_motion_seed.py` would already have caught. */
export function seededMotion(id: string): {
  full: MotionVocabulary;
  reduced: MotionVocabulary;
} {
  return fromMotionRecord(seededMotionRecord(id));
}
