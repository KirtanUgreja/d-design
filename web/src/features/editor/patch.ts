// The one place a patch is applied and the one place it is validated
// (docs/v1/plan/09-editor.md -> "One patch shape, two producers"). Pure, and
// deliberately outside the store: the property panel and the element-scoped
// prompt both land here, and neither React nor Zustand is involved in deciding
// whether an edit is legal.

import { err, ok, type Result } from '@/lib/result';
import { blockSchema, sceneSchema, type BlockPatch, type Scene } from '@/schema';

/** Props a patch may never carry.
 *
 * `type` is the discriminator, and holding it immutable is what makes offline
 * validation *sound* rather than merely convenient. The whole-tree rules —
 * at most one Headline per scene, unique block ids, a region that exists on
 * the layout, grid cell counts — live in Pydantic and do not cross into Zod,
 * because JSON Schema has no vocabulary for a predicate over a whole tree
 * (docs/coderules/typescript.md). The editor can still be trusted to reject a
 * bad edit without a round trip precisely because a props-only patch that
 * cannot change `type` cannot reach any of them: it cannot turn an Eyebrow
 * into a second Headline, and `region` is a field on `Block` rather than on
 * `props`, so a patch cannot move a block into a region the layout lacks
 * either.
 *
 * Mirroring those rules in TypeScript was the alternative and is the one thing
 * the rules forbid — a second copy drifts, and the copy is the bug.
 */
const IMMUTABLE_PROPS = ['type'] as const;

/** Apply a patch, or say why not. The previous tree is never mutated.
 *
 * Untouched scenes and blocks come back by reference, not by copy. That is the
 * structural sharing undo/redo needs, and it is also what makes
 * "only the target block changed" checkable by identity rather than by a deep
 * compare that could pass while something was quietly rebuilt.
 */
export function applyPatch(scenes: Scene[], patch: BlockPatch): Result<Scene[]> {
  const scene = scenes.find((s) => s.id === patch.sceneId);
  if (!scene) return err('not_found', `no scene ${patch.sceneId}`);

  const block = scene.blocks.find((b) => b.id === patch.blockId);
  if (!block) return err('not_found', `no block ${patch.blockId}`);

  for (const key of IMMUTABLE_PROPS) {
    if (key in patch.props && patch.props[key] !== block.props[key]) {
      return err('invalid_input', `${key} cannot be changed by an edit`);
    }
  }

  // One parse, at the boundary, on the merged result — not on the partial.
  // A patch is external input whether a panel or a model produced it, and a
  // partial cannot be validated on its own: `{ text: '' }` is only illegal
  // once you know which block it lands on.
  const merged = blockSchema.safeParse({
    ...block,
    props: { ...block.props, ...patch.props },
  });
  if (!merged.success) return err('invalid_input', firstIssue(merged.error));

  const blocks = scene.blocks.map((b) => (b.id === patch.blockId ? merged.data : b));

  // Validate the scene, then throw the parsed value away and keep the objects
  // built above. That is not belt-and-braces, it is the whole point: Zod
  // applies defaults on parse, so `sceneSchema.parse` returns a tree in which
  // *every* block is a fresh object carrying `motion: 'reveal'`, `region:
  // null` and so on. Using it would rebuild untouched blocks on every
  // keystroke — new identities, so React re-renders the scene rather than the
  // one block, which is exactly what hot path 3 forbids
  // (docs/coderules/performance.md). The parse is the check; the map is the
  // result.
  const checked = sceneSchema.safeParse({ ...scene, blocks });
  if (!checked.success) return err('invalid_input', firstIssue(checked.error));

  return ok(scenes.map((s) => (s.id === patch.sceneId ? { ...scene, blocks } : s)));
}

/** The panel shows one message, so it gets the first problem rather than a
 * serialized issue array. Zod's own text, and the path, and nothing the user
 * typed — an over-long headline's error should not quote the headline. */
function firstIssue(error: {
  issues: { path: PropertyKey[]; message: string }[];
}): string {
  const issue = error.issues[0];
  if (!issue) return 'invalid';
  const path = issue.path.map(String).filter((p) => p !== 'props');
  return path.length > 0 ? `${path.join('.')}: ${issue.message}` : issue.message;
}
