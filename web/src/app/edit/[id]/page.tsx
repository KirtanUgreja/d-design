// The editor's route. Loads the experience by id from `api`, and falls back to
// the phase 01 `full` fixture when there is none — so the editor stays
// reachable and judgeable without paying for a generation first, the same
// reason /dev/primitives reads fixtures rather than calling the pipeline.
//
// The fixture branch was the *only* branch until the acceptance pass: nothing
// persisted a built experience, so there was no id that could resolve. `/new`
// now creates one and redirects here, which is what makes "build → edit →
// publish" a single path rather than three demos.
//
// A fixture-loaded editor cannot publish — `saveScenes` 404s on an id `api`
// has never seen — and that is the correct outcome rather than a gap. The
// screen is told which one it is holding so it can say so instead of failing
// at the click.

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { notFound } from 'next/navigation';

import { loadArtDirection, loadMotion } from '@/features/art-direction/server';
import { readExperience } from '@/features/publish';
import { experienceSchema } from '@/schema';

import { EditorScreen } from './editor-screen';

const FIXTURES = join(process.cwd(), '..', 'api', 'schema', 'fixtures');

function fixture() {
  return experienceSchema.parse(
    JSON.parse(readFileSync(join(FIXTURES, 'full.json'), 'utf8')),
  );
}

export default async function EditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const loaded = await readExperience(id);
  const experience = loaded.ok ? loaded.value : fixture();

  // The art direction is resolved here, on the server, and handed down as
  // tokens. The editor canvas is a client component and the store read is
  // `server-only`, which is the boundary doing its job rather than an
  // inconvenience: what-you-edit-is-what-you-ship means the canvas renders the
  // direction the artifact will publish under, and that is a fact the server
  // establishes once instead of something the browser re-derives.
  // Two reads, because they are two axes. Resolved together here only because
  // this page needs both; nothing in the store joins them, and the day the
  // editor offers a motion picker it changes one of these calls and not the
  // other.
  const [resolved, motion] = await Promise.all([
    loadArtDirection(experience.artDirection),
    loadMotion(experience.motionVocabulary),
  ]);
  if (!resolved.ok || !motion.ok) notFound();

  return (
    <EditorScreen
      experienceId={id}
      title={experience.title}
      artDirection={resolved.value.artDirection}
      // The full vocabulary. The editor canvas is a working surface rather
      // than a presentation, and the reduced floor belongs to the reader of a
      // published page — `PresentedExperience` is where the swap lives.
      motion={motion.value.full}
      initialScenes={experience.scenes}
      stored={loaded.ok}
    />
  );
}
