// The stored vocabulary -> the two objects the wrapper chooses between.
//
// The motion half of the seam `from-record.ts` is for art directions, and the
// place v1's `resolveArtDirection` code table finally goes: a vocabulary is no
// longer something an art direction comes with, it is something an experience
// points at.
//
// **Two shapes, one mapping, and the shapes differ on purpose.** The record is
// authored per concept — one ease, two durations, two distances — because that
// is how the values get decided, and because an authoring form with four
// near-identical intent blocks invites four inconsistent answers to one
// question. The renderer indexes by intent, because that is how a block asks:
// `vocabulary.intents[block.motion]`. Everything below is that translation, and
// it is the only copy of it.
//
// **`parallax` and `none` are derived, not stored.** Parallax is scroll-linked,
// so its duration is however long the reader scrolls and its `distancePx` is
// the clamp bound the wrapper computes against. `none` is off. Neither is a
// number anyone authors, and giving them fields would invite someone to fill
// them in — which is how a vocabulary ends up with a `none` that animates.
//
// Nothing here reads the environment (rule 6). Which of the two returned
// vocabularies is used *is* an environment read, and it stays in the wrapper
// where it has always been (`features/present/motion-toggle.tsx`).

import type { MotionVocabularyRecord } from '@/schema';

import type { Easing, MotionIntentDef, MotionVocabulary } from './motion-vocabulary';

/** Four numbers into the tuple the renderer's type declares.
 *
 * The schema types a bezier as `number[]` with a length of exactly four, which
 * is as close as JSON Schema gets to a tuple. `noUncheckedIndexedAccess` is on,
 * so the four are narrowed here rather than asserted with `!` — and a record
 * that somehow carried three would throw rather than produce a curve with an
 * `undefined` in it. */
function toEasing(value: number[]): Easing {
  const [a, b, c, d] = value;
  if (a === undefined || b === undefined || c === undefined || d === undefined) {
    throw new Error('from-motion-record: an easing has fewer than four components');
  }
  return [a, b, c, d];
}

/** The intent that does not move: zero duration, zero travel, no scaling.
 *
 * Derived rather than stored, and it takes the vocabulary's own easing anyway —
 * an easing on a zero-duration animation is inert, and giving it a different
 * curve from its siblings would be a difference that means nothing and reads
 * like it means something. */
function still(ease: Easing): MotionIntentDef {
  return { durationMs: 0, distancePx: 0, scale: 1, ease };
}

export function fromMotionRecord(record: MotionVocabularyRecord): {
  full: MotionVocabulary;
  reduced: MotionVocabulary;
} {
  const ease = toEasing(record.ease);
  const easeEmphasis = toEasing(record.easeEmphasis);

  const full: MotionVocabulary = {
    intents: {
      reveal: {
        durationMs: record.durations.reveal,
        distancePx: record.distances.revealY,
        scale: 1,
        ease,
      },
      emphasize: {
        durationMs: record.durations.emphasize,
        distancePx: 0,
        scale: record.distances.emphasizeScale,
        ease: easeEmphasis,
      },
      // Duration 0 because the travel is scroll-linked: the wrapper computes an
      // offset each frame and `distancePx` is how far it may go, not how far it
      // goes. That inversion is why parallax has no stored duration.
      parallax: {
        durationMs: 0,
        distancePx: record.distances.parallaxFactor,
        scale: 1,
        ease,
      },
      none: still(ease),
    },
    staggerMs: record.stagger,
    staggerCap: record.staggerCap,
    triggerRatio: record.trigger,
  };

  return { full, reduced: toReduced(record, ease) };
}

/** The accessibility floor for this vocabulary.
 *
 * **Opacity only, for every intent, with no transform and no parallax** — WCAG
 * 2.3.3, and docs/v1/art-direction.md is explicit that this is a design
 * requirement for this product rather than a checkbox: parallax is a documented
 * vestibular trigger. Built here rather than stored, so there is no shape in
 * which a vocabulary could declare a reduced mode that moves. The record
 * carries one number — the duration — because that is the only part of the
 * floor that is a design decision.
 *
 * **Two things about it changed with the format, both deliberate.** v1 had one
 * global `REDUCED_MOTION` shared by both vocabularies; now each fades on its
 * own easing and fires at its own trigger. The durations are unchanged, so a
 * reader with the preference set sees the same timing they saw before — what
 * they get instead of a borrowed curve is the vocabulary being itself, quietly.
 * That is the whole reason the phase makes reduced motion per-vocabulary:
 * 200ms under `mechanical-snap` and 200ms under `physics-playful` are not the
 * same design even when both are a bare fade.
 */
function toReduced(record: MotionVocabularyRecord, ease: Easing): MotionVocabulary {
  const fade: MotionIntentDef = {
    durationMs: record.reducedMotion.duration,
    distancePx: 0,
    scale: 1,
    ease,
  };
  return {
    intents: {
      reveal: fade,
      emphasize: fade,
      parallax: fade,
      // Still zero rather than the fade. `none` means the author said this does
      // not animate, and reduced motion is not an instruction to start.
      none: still(ease),
    },
    // No stagger. A sequence is a movement, and the floor has none.
    staggerMs: 0,
    staggerCap: record.staggerCap,
    triggerRatio: record.trigger,
  };
}
