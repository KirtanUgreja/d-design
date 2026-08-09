'use server';

// Publishing, as the editor calls it — phase 05 built `publishExperience` and
// left a `/dev/publish/[id]` route as its only trigger, noting that "the editor
// calls the same feature function from a real UI in phase 09". This is that,
// and those two dev routes are deleted rather than kept: a second way to
// publish that nothing calls is a path that rots without anyone noticing.
//
// A Server Action, not a client fetch, because publishing writes the artifact
// to local disk and needs `API_URL` — both server-only concerns
// (docs/coderules/structure.md -> "The server/client boundary"). App-level
// composition of one feature, so it lives in the route tree.
//
// **Server Actions are public HTTP endpoints.** In v1 that means: this one
// takes a caller-supplied id, and every authorization decision behind it
// happens at the data layer through `as_user()` in `api` — this file adds no
// check of its own and must not look as though it does. When there are real
// sessions, the session check goes here *and* stays there.

import { publishExperience, saveScenes, unpublishExperience } from '@/features/publish';
import type { AppError } from '@/lib/result';
import { sceneSchema } from '@/schema';
import { z } from 'zod';

const scenesSchema = z.array(sceneSchema);

/** Save the edited tree, then ship it. Two steps, in this order, deliberately:
 * `publishExperience` freezes whatever is stored, so publishing without saving
 * first would ship the pre-edit scenes and look like the edit was lost.
 *
 * The scenes arrive from a browser over an HTTP endpoint, so they are external
 * input and get the one parse every external input gets — a Server Action's
 * arguments are not typed at runtime just because they are typed at the call
 * site (docs/coderules/typescript.md). */
export async function publishEdited(
  id: string,
  scenes: unknown,
): Promise<{ ok: true } | { ok: false; error: AppError }> {
  const parsed = scenesSchema.safeParse(scenes);
  if (!parsed.success) {
    return { ok: false, error: { code: 'invalid_input', message: parsed.error.message } };
  }

  const saved = await saveScenes(id, parsed.data);
  if (!saved.ok) return saved;

  const published = await publishExperience(id);
  if (!published.ok) return published;
  return { ok: true };
}

/** Taking it down again, which is the half of publishing that decides whether
 * a person feels safe doing the first half. */
export async function unpublishEdited(
  id: string,
): Promise<{ ok: true } | { ok: false; error: AppError }> {
  const result = await unpublishExperience(id);
  if (!result.ok) return result;
  return { ok: true };
}
