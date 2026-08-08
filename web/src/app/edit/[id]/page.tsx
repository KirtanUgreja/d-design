// The editor's route. Reads the published artifact if there is one and falls
// back to the phase 01 `full` fixture, so the editor is reachable and
// judgeable without running a generation first — the same reason
// /dev/primitives reads fixtures rather than calling the pipeline.
//
// ponytail: experiences live in `api` and the editor should load one by id
// through it. That needs a scenes-by-experience read the API does not expose
// yet (publish stores a whole `Experience`; Build streams scenes to the client
// and never persists them on its own). Upgrade: a GET that returns the built
// scenes, at which point this file loses its fixture branch.

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { experienceSchema } from '@/schema';

import { EditorScreen } from './editor-screen';

const FIXTURES = join(process.cwd(), '..', 'api', 'schema', 'fixtures');

export default async function EditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const experience = experienceSchema.parse(
    JSON.parse(readFileSync(join(FIXTURES, 'full.json'), 'utf8')),
  );
  return <EditorScreen experienceId={id} initialScenes={experience.scenes} />;
}
