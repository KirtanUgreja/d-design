// The fifth token group, shipped separately from `ArtDirection` on purpose.
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
  /** IntersectionObserver threshold — how much of an element must be visible
   * before its motion fires. Fires once. */
  triggerRatio: number;
}

const EXPO_OUT: Easing = [0.16, 1, 0.3, 1];
const EASE_EMPHASIS: Easing = [0.22, 1, 0.36, 1];

export const CINEMATIC_MOTION: MotionVocabulary = {
  intents: {
    reveal: { durationMs: 900, distancePx: 32, scale: 1, ease: EXPO_OUT },
    emphasize: { durationMs: 1100, distancePx: 0, scale: 0.96, ease: EASE_EMPHASIS },
    // Parallax's distance is a clamp (±80px), not a fixed offset — it is
    // scroll-linked and computed by the wrapper each frame, not by this
    // vocabulary. distancePx here is the clamp bound.
    parallax: { durationMs: 0, distancePx: 80, scale: 1, ease: EXPO_OUT },
    none: { durationMs: 0, distancePx: 0, scale: 1, ease: EXPO_OUT },
  },
  staggerMs: 120,
  triggerRatio: 0.25,
};

const EASE_EDITORIAL: Easing = [0.32, 0.72, 0, 1];

/** `editorial-light`'s vocabulary — motion that *arrives* rather than drifts.
 *
 * Motion is a token group like the other four, and it is the one where using
 * the wrong direction's values is most obviously wrong: a printed spread that
 * eases in over 900ms with a 120ms stagger is a slideshow pretending to be a
 * page. Roughly a third of cinematic-dark's duration, a third of its travel,
 * and a stagger short enough to read as one movement rather than a sequence.
 *
 * `emphasize` scales *up* from 0.99 — barely — where cinematic-dark scales up
 * from 0.96. A print page does not swell. `parallax` keeps a real but small
 * travel: zero would be a lie the token layer should not tell, since the
 * schema still lets a scene ask for it. */
export const EDITORIAL_MOTION: MotionVocabulary = {
  intents: {
    reveal: { durationMs: 320, distancePx: 12, scale: 1, ease: EASE_EDITORIAL },
    emphasize: { durationMs: 360, distancePx: 0, scale: 0.99, ease: EASE_EDITORIAL },
    parallax: { durationMs: 0, distancePx: 24, scale: 1, ease: EASE_EDITORIAL },
    none: { durationMs: 0, distancePx: 0, scale: 1, ease: EASE_EDITORIAL },
  },
  staggerMs: 40,
  // Fires later than cinematic-dark's 0.25: short motion that starts while the
  // block is barely on screen has finished before anyone is looking at it.
  triggerRatio: 0.4,
};

/** Every intent collapses to opacity-only, 200ms, no transform, no parallax —
 * WCAG 2.3.3, and art-direction.md is explicit this is a design requirement
 * for this product, not a checkbox: parallax is a documented vestibular
 * trigger. */
export const REDUCED_MOTION: MotionVocabulary = {
  intents: {
    reveal: { durationMs: 200, distancePx: 0, scale: 1, ease: EXPO_OUT },
    emphasize: { durationMs: 200, distancePx: 0, scale: 1, ease: EXPO_OUT },
    parallax: { durationMs: 200, distancePx: 0, scale: 1, ease: EXPO_OUT },
    none: { durationMs: 0, distancePx: 0, scale: 1, ease: EXPO_OUT },
  },
  staggerMs: 0,
  triggerRatio: 0.25,
};

const MAX_STAGGER_SIBLINGS = 5;

/** Stagger is derived from block index within a region, capped at 5. Never
 * authored, never in the schema — computed here so every call site agrees. */
export function staggerDelayMs(
  vocabulary: MotionVocabulary,
  indexInRegion: number,
): number {
  const capped = Math.min(Math.max(indexInRegion, 0), MAX_STAGGER_SIBLINGS);
  return vocabulary.staggerMs * capped;
}
