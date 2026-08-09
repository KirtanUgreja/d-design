import 'server-only';

// Publishing is a render, not a route (docs/v1/plan/05-publish-present-embed.md):
// fetch the validated Experience from `api`, freeze the fields a page needs
// to render into an artifact, write it once. Serving reads that artifact
// straight off disk — no database query, no call to `api`, per view.
//
// The renderer itself does the actual `renderToString` equivalent, inside
// Next's own page-rendering pipeline, when `/p/[id]/page.tsx` reads this
// artifact — reusing the pipeline that already works rather than hand-
// rolling a second one that has to independently ship a hydration bundle.

import { z } from 'zod';

import { err, ok, type Result } from '@/lib/result';
import { deleteArtifact, readArtifact, writeArtifact } from '@/lib/storage';
import { experienceSchema, sceneSchema, type Experience, type Scene } from '@/schema';

const publishedArtifactSchema = z.strictObject({
  title: z.string(),
  mode: z.enum(['scroll', 'slides']),
  artDirection: z.literal('cinematic-dark'),
  scenes: z.array(sceneSchema),
  publishedAt: z.string(),
});

export type PublishedArtifact = z.infer<typeof publishedArtifactSchema>;

function apiUrl(): string {
  const url = process.env.API_URL;
  if (!url) throw new Error('API_URL is not set');
  return url;
}

/** The one read of a stored `Experience`, shared by everything on this side
 * that needs one — publishing, saving an edit, and the editor route loading
 * the thing it is about to edit.
 *
 * Extracted in the acceptance pass, when the editor stopped reading a fixture:
 * three call sites were about to spell the same fetch-parse-or-404 three
 * times, which is the duplication ai-authorship.md measures. `cache: 'no-store'`
 * on all of them — an editor that opens a cached copy of the scenes it is
 * about to overwrite is a lost edit. */
export async function readExperience(id: string): Promise<Result<Experience>> {
  // `api` being down is an expected failure of an external service, not a bug
  // in this process, so it returns a `Result` like every other expected failure
  // (docs/coderules/README.md rule 3). A bare `fetch` here *throws* on a
  // refused connection, which turned the editor route into a 500 the first time
  // it was opened without `api` running — and the editor is exactly the page
  // that has a designed answer for this, since it can fall back to the fixture.
  let res: Response;
  try {
    res = await fetch(`${apiUrl()}/experiences/${id}`, { cache: 'no-store' });
  } catch (e) {
    return err(
      'upstream_unavailable',
      e instanceof Error ? e.message : 'api unreachable',
    );
  }
  if (!res.ok) {
    return err(
      res.status === 404 ? 'not_found' : 'upstream_unavailable',
      await res.text(),
    );
  }
  const parsed = experienceSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}

/** Persist edited scenes against the experience they came from.
 *
 * Read-then-replace rather than a scenes-only endpoint, because `api`'s
 * `PUT /experiences/{id}` takes a whole `Experience` and re-runs the
 * structural validators on it (one hook first, at least one CTA, at most one
 * Slot). Those rules are about the *tree*, so an edit that breaks one has to
 * be refused, and the only way to get that for free is to hand the whole tree
 * back. The read is what supplies the fields the editor does not own — title,
 * mode, brand — so it cannot silently reset them to a client's guess. */
export async function saveScenes(id: string, scenes: Scene[]): Promise<Result<void>> {
  const current = await readExperience(id);
  if (!current.ok) return current;

  const res = await fetch(`${apiUrl()}/experiences/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...current.value, scenes }),
  });
  if (!res.ok) {
    return err(
      res.status === 422 ? 'invalid_input' : 'upstream_unavailable',
      await res.text(),
    );
  }
  return ok(undefined);
}

export async function publishExperience(id: string): Promise<Result<void>> {
  const parsed = await readExperience(id);
  if (!parsed.ok) return parsed;

  const experience = parsed.value;
  const artifact: PublishedArtifact = {
    title: experience.title,
    mode: experience.mode,
    artDirection: experience.artDirection,
    scenes: experience.scenes,
    publishedAt: new Date().toISOString(),
  };
  const written = await writeArtifact(id, artifact);
  if (!written.ok) return written;

  const publishRes = await fetch(`${apiUrl()}/experiences/${id}/publish`, {
    method: 'POST',
  });
  if (!publishRes.ok) {
    return err('upstream_unavailable', await publishRes.text());
  }
  return ok(undefined);
}

export async function unpublishExperience(id: string): Promise<Result<void>> {
  const res = await fetch(`${apiUrl()}/experiences/${id}/unpublish`, { method: 'POST' });
  if (!res.ok) {
    return err(
      res.status === 404 ? 'not_found' : 'upstream_unavailable',
      await res.text(),
    );
  }
  return deleteArtifact(id);
}

/** The one read path `/p/[id]` and `/e/[id]` both call. Re-validated here,
 * not just trusted from the write side — a fresh request handler reading a
 * file is a boundary too, and a corrupted artifact should 404, not crash. */
export async function readPublishedArtifact(
  id: string,
): Promise<Result<PublishedArtifact>> {
  const raw = await readArtifact(id);
  if (!raw.ok) return raw;
  const parsed = publishedArtifactSchema.safeParse(raw.value);
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}
