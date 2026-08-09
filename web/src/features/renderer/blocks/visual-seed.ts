// The one PRNG and the one intensity scale, shared by all five AbstractVisual
// generators (docs/v1/plan/11-visuals-and-slot.md -> Search: "The other four
// extend it; they do not become four new components with four copies of the
// seed logic").
//
// Why a shared seed module rather than a shared component: the five look
// nothing alike — blobs, dots, lines, an orb, a veil — so a common render path
// would be a switch pretending to be an abstraction. What they genuinely share
// is *determinism*, and that is this file.
//
// **No user string reaches any generator.** `generator` is an enum and `seed`
// is a number, which is the entire reason `AbstractVisual` needs no XSS
// treatment and why `assertNoPresentationalValues` has nothing to find in one.

import type { AbstractVisualProps } from './block-props';

/** mulberry32 — tiny, fast, seedable. Not cryptographic and does not need to
 * be: this seeds visual placement, not a security decision. */
export function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type Intensity = AbstractVisualProps['intensity'];

/** One place the three intensities mean something, so `subtle` is comparably
 * subtle across all five generators rather than each having its own idea. A
 * scene that switches generator should change character, not loudness. */
export const INTENSITY: Record<Intensity, { count: number; opacity: number }> = {
  subtle: { count: 2, opacity: 0.25 },
  medium: { count: 3, opacity: 0.45 },
  bold: { count: 4, opacity: 0.7 },
};

/** A stable 32-bit hash of a scene id.
 *
 * The seed a generator actually uses is derived from the scene id on the
 * server (`api/features/generation/visuals.py`), so the same scene always
 * looks the same and a rebuild is not a visual change nobody asked for. This
 * function is the client-side half of that contract: the editor's reroll
 * writes a fresh number, and anything else that needs a seed without one
 * derives it the same way rather than reaching for `Math.random`.
 *
 * FNV-1a over **UTF-8 bytes**, matching the Python implementation exactly —
 * the two are asserted equal in `renderer.test.ts` and `tests/test_visual_seed.py`
 * against one shared fixture table.
 *
 * `TextEncoder`, not `charCodeAt`: the obvious version of this loop walks
 * UTF-16 code units and masks each to a byte, which agrees with Python's
 * `.encode("utf-8")` for ASCII and silently disagrees for everything else. A
 * scene id is model-generated, and this codebase has already watched a model
 * emit CJK into a text field, so "ids are ASCII in practice" is not a
 * property to hash on.
 */
export function seedFromId(id: string): number {
  let hash = 0x811c9dc5;
  for (const byte of new TextEncoder().encode(id)) {
    hash ^= byte;
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  // Clamped to the schema's own `seed` range (0 .. 2^31-1), so a derived seed
  // is always a value the schema would accept.
  return hash % 2147483647;
}
