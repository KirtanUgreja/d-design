// The standing judgment surface for the rest of v1 (docs/v1/plan/04-renderer.md).
// Every one of the 11 primitives, every one of the 6 layouts, under
// cinematic-dark, driven by the phase 01 fixtures — including hostile.json,
// the fixture that predicts real briefs (maximum-length copy in every field).
//
// Not part of the published artifact — dev-only, and outside src/features/renderer/,
// so ordinary app chrome (Tailwind) is fair game for the harness controls.

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import {
  seededArtDirections,
  seededMotion,
  seededMotionRecords,
} from '@/features/art-direction/server';
import { experienceSchema } from '@/schema';

import { PrimitivesHarness } from './primitives-harness';

// import.meta.dirname isn't populated in Turbopack's SSR bundle for this
// route; process.cwd() is `web/` for both `next dev` and `next build`.
const FIXTURES = join(process.cwd(), '..', 'api', 'schema', 'fixtures');
const readFixture = (name: string) =>
  experienceSchema.parse(
    JSON.parse(readFileSync(join(FIXTURES, `${name}.json`), 'utf8')),
  );

export default function PrimitivesPage() {
  const experiences = {
    minimal: readFixture('minimal'),
    full: readFixture('full'),
    hostile: readFixture('hostile'),
  };

  // The seeded records off disk rather than a store read: this harness exists
  // to look at tokens with nothing else running, and requiring `api` to be up
  // to see a type scale would be the wrong trade for the one page whose whole
  // job is judging the token layer.
  const motionVocabularies = seededMotionRecords().map((record) => ({
    id: record.id,
    ...seededMotion(record.id),
  }));

  return (
    <PrimitivesHarness
      experiences={experiences}
      artDirections={seededArtDirections()}
      motionVocabularies={motionVocabularies}
    />
  );
}
