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
import { experienceSchema, sceneSchema } from '@/schema';

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

export async function publishExperience(id: string): Promise<Result<void>> {
  const getRes = await fetch(`${apiUrl()}/experiences/${id}`, { cache: 'no-store' });
  if (!getRes.ok) {
    return err(
      getRes.status === 404 ? 'not_found' : 'upstream_unavailable',
      await getRes.text(),
    );
  }

  const parsed = experienceSchema.safeParse(await getRes.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);

  const experience = parsed.data;
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
