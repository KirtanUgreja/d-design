// The fifth token group — and as of v2 phase 02, its own axis.
//
// **Types only. The values are rows.** `CINEMATIC_MOTION` and
// `EDITORIAL_MOTION` lived here as constants, paired to an art direction by a
// code table, so choosing a look chose the motion with it. They are
// `cinematic-slow` and `editorial-restrained` in `motion_vocabularies` now,
// seeded from `api/features/motion/seed.py` with the same numbers, and
// `from-motion-record.ts` is the one place a row becomes one of these objects.
//
// The shape below is what the *renderer* reads — indexed by intent, because
// that is how a block asks. The stored shape is authored per concept (one ease,
// two durations, two distances), because that is how the values are decided.
// `schema/motion.py` explains why the two differ and where the mapping lives.
//
// The renderer core is pure and may not read `typeof window`
// (docs/coderules/patterns.md rule 6), so the reduced-motion collapse cannot
// live inside a block component or be derived from a media-query read buried
// in here — it lives as a second, complete vocabulary the WRAPPER chooses
// between. That is why `SceneRenderer(tree, artDirection, motion)` takes
// motion as its own parameter: two swappable objects, not one object with an
// environment-dependent field.
//
// Nothing in this file reads the environment. It is data, and it is tested
// as data (art-direction.test.ts asserts exactly that).

import type { Block } from '@/schema';

export type MotionIntent = NonNullable<Block['motion']>; // 'reveal' | 'emphasize' | 'parallax' | 'none'

export type Easing = readonly [number, number, number, number];

export interface MotionIntentDef {
  durationMs: number;
  /** px, applied as translateY for reveal/parallax. 0 where transform isn't a translate. */
  distancePx: number;
  /** unitless scale factor for emphasize; 1 (no-op) elsewhere. */
  scale: number;
  ease: Easing;
}

export interface MotionVocabulary {
  intents: Record<MotionIntent, MotionIntentDef>;
  /** ms per sibling index, before the stagger cap is applied. */
  staggerMs: number;
  /** How many siblings the stagger accumulates over before it stops. A field
   * rather than the module constant it was in v1 — see `staggerDelayMs`. */
  staggerCap: number;
  /** IntersectionObserver threshold — how much of an element must be visible
   * before its motion fires. Fires once. */
  triggerRatio: number;
}

/** The number of siblings after which stagger stops accumulating.
 *
 * A module constant in v1 and a field on the vocabulary since phase 02, because
 * "how long a sequence still reads as one movement" is a property of the
 * motion, not of the renderer — a nine-item list under a 120ms stagger is a
 * second of dead time whatever the art direction. This function is still the
 * only place the cap is applied, which is what keeps every call site agreeing.
 *
 * Stagger is derived from block index within a region. Never authored, never in
 * the schema.
 */
export function staggerDelayMs(
  vocabulary: MotionVocabulary,
  indexInRegion: number,
): number {
  const capped = Math.min(Math.max(indexInRegion, 0), vocabulary.staggerCap);
  return vocabulary.staggerMs * capped;
}
