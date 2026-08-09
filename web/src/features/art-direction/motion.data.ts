import 'server-only';

// Reading a motion vocabulary out of the store. The other half of what
// `resolveArtDirection`'s code table used to do in one step.
//
// Separate from `art-direction.data.ts` because they are separate axes now,
// and folding them into one "resolve the experience's styling" call would be
// the code table growing back with a network hop in it — an experience picks
// two things and the two are picked independently.
//
// No version in the URL. `MotionVocabularyRef` explains why: an art direction
// is user-editable and a page pinned to one has to name a version or it
// restyles itself when its author edits it; a motion vocabulary is a system row
// whose new version is a reviewed migration, and a published page freezes the
// resolved vocabulary in its artifact regardless.

import type { MotionVocabularyRef } from '@/schema';
import { motionVocabularyRecordSchema } from '@/schema';
import { err, ok, type Result } from '@/lib/result';

import { fromMotionRecord } from './from-motion-record';
import type { MotionVocabulary } from './motion-vocabulary';

function apiUrl(): string {
  const url = process.env.API_URL;
  if (!url) throw new Error('API_URL is not set');
  return url;
}

export interface ResolvedMotion {
  /** What it was resolved from. Publish freezes this into the artifact; the
   * renderer never looks at it. */
  record: ReturnType<typeof motionVocabularyRecordSchema.parse>;
  /** The vocabulary as authored. */
  full: MotionVocabulary;
  /** The same vocabulary collapsed to opacity — the floor the wrapper swaps in
   * when the reader asks for it. Built here rather than stored, so there is no
   * shape in which a vocabulary could declare a reduced mode that moves. */
  reduced: MotionVocabulary;
}

export async function loadMotion(
  ref: MotionVocabularyRef,
): Promise<Result<ResolvedMotion>> {
  let res: Response;
  try {
    res = await fetch(`${apiUrl()}/motion-vocabularies/${encodeURIComponent(ref.id)}`, {
      cache: 'no-store',
    });
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

  const parsed = motionVocabularyRecordSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok({ record: parsed.data, ...fromMotionRecord(parsed.data) });
}

/** Every vocabulary, newest version of each — what a picker offers when there
 * is one. Phase 11 builds it; two vocabularies do not need a UI. */
export async function listMotionVocabularies(): Promise<
  Result<ReturnType<typeof motionVocabularyRecordSchema.parse>[]>
> {
  let res: Response;
  try {
    res = await fetch(`${apiUrl()}/motion-vocabularies`, { cache: 'no-store' });
  } catch (e) {
    return err(
      'upstream_unavailable',
      e instanceof Error ? e.message : 'api unreachable',
    );
  }
  if (!res.ok) return err('upstream_unavailable', await res.text());

  const parsed = motionVocabularyRecordSchema.array().safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}
