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

  return (
    <EditorScreen
      experienceId={id}
      title={experience.title}
      initialScenes={experience.scenes}
      stored={loaded.ok}
    />
  );
}
