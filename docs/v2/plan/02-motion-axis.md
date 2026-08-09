# Phase 02 — Motion as an independent axis

> Motion stops belonging to an art direction and becomes a thing you choose. Three art directions × four vocabularies = twelve combinations from seven authored artifacts, and that ratio is the entire argument.

**Depends on:** [01](01-ad-format.md) · **Blocks:** [04](04-three-art-directions.md), [11](11-range.md) · **Spec step:** 2

> **Done, 2026-08-09.** `cinematic-slow` and `editorial-restrained` are rows in `motion_vocabularies`, seeded by migration 0012, and both produce objects **byte-identical** to v1's constants. `resolveArtDirection`'s pairing is gone: `fromRecord` hands back tokens and no vocabulary with them, and an experience carries its own reference. What the phase found on the way is under "What actually happened".

---

## Search

**Read first**

- [../art-direction-system.md](../art-direction-system.md) → "Motion as an independent axis" — the `MotionVocabulary` shape, including `slidesVariant` and `reducedMotion`
- [../../coderules/patterns.md](../../coderules/patterns.md) → rule 6, the reason `SceneRenderer` takes motion as its own parameter and always did

**Grep for**

- `web/src/features/art-direction/motion-vocabulary.ts` — `CINEMATIC_MOTION`, `EDITORIAL_MOTION`, `REDUCED_MOTION`, `staggerDelayMs`. The data already exists and is already pure; this phase moves where it lives, not what it says
- `web/src/features/present/motion-toggle.tsx` — `useMotionPreference(full)` already takes the vocabulary as an argument rather than picking one. v1's art direction #2 work did that; do not undo it
- `web/src/features/renderer/motion/reveal.tsx` — the wrapper that reads a vocabulary. **It must not learn a fourth intent in this phase**, and if a vocabulary needs one, that is the format being wrong

**Verify externally** — nothing. This is a move plus a persistence layer.

---

## Make

```
api/schema/motion.py                MotionVocabulary, Pydantic-owned
api/features/motion/
  __init__.py                       load, list
  motion_data.py                    SQLAlchemy, motion_vocabularies only
web/src/features/art-direction/
  motion-vocabulary.ts              types only; values move to the store
api/migrations/versions/            seed cinematic-slow, editorial-restrained
```

### The shape, and the two fields v1 does not have

```
MotionVocabulary {
  id, version
  ease, easeEmphasis                  parsed [a,b,c,d], never a string
  durations { reveal, emphasize }
  distances { revealY, parallaxFactor }
  stagger, staggerCap, trigger
  slidesVariant { durations, trigger: 'advance' }
  reducedMotion { duration }          opacity only
}
```

**`slidesVariant` is why slides mode is a lookup rather than a code path.** Phase 10 reads it; nothing else does. Authoring it now costs four numbers per vocabulary and saves phase 10 from inventing a second timing system.

**`reducedMotion` is a required field, not a fallback.** v1 has one global `REDUCED_MOTION` constant, and that was correct while there was one vocabulary. It stays a floor — no vocabulary gets a louder reduced mode — but each one declares its duration, because 200ms under `mechanical-snap` and 200ms under `physics-playful` are not the same design even when both are opacity-only.

### `cinematic-slow` and `editorial-restrained` are renames of what exists

v1's `CINEMATIC_MOTION` becomes `cinematic-slow` v1. `EDITORIAL_MOTION` becomes `editorial-restrained` v1. Same numbers.

Two vocabularies now, not four. `mechanical-snap` and `physics-playful` are phase 11, and building them here would be authoring motion for art directions that do not exist yet — the exact mistake the build order is arranged to avoid.

### The experience gains a reference

`experiences.motion_vocabulary` was added in phase 00 and is populated here. The rule that keeps the surface curated:

- The **art direction's `defaultMotion`** is what an experience gets when it is created or reskinned without an explicit choice
- An explicit choice on the experience **wins and persists** across a reskin

That second half is the one worth being deliberate about. Reskinning to `bold-brutalist` should not silently discard a user's motion choice; changing the art direction is not changing the motion. The reskin flow in phase 07 offers the new default and does not apply it.

### What must not happen

The renderer already takes `motion` as a parameter and reads only what it is given. **Nothing in this phase adds a branch on which vocabulary it received**, and nothing adds a fourth `MotionIntent`. The schema's `Block.motion` union — `reveal | emphasize | parallax | none` — is the contract; a vocabulary varies the values of those four and never their number.

---

## Verify

**The gate** — green, schema regenerates with no diff.

**The axis**

- [x] `cinematic-slow` and `editorial-restrained` produce byte-identical objects to v1's constants — asserted against `motion_v1.json`, captured as the constants were deleted. Objects rather than CSS: a vocabulary is passed to the renderer, never emitted as custom properties
- [x] Every one of the 2 × 2 art-direction/vocabulary combinations renders the `full` fixture without a crash — `/dev/primitives` has two independent selectors now, and no combination resets the other
- [x] An experience with an explicit motion choice keeps it across a reskin; one without picks up the new art direction's default — the field is required with no schema default, so "what a new experience inherits" is a decision made where experiences are created rather than a value that appears when nobody said
- [x] `staggerDelayMs` still caps at 5 siblings, computed in one place — the cap became a field, and a test asserts both vocabularies still declare 5

**Reduced motion**

- [x] Every vocabulary's `reducedMotion` is opacity-only, no transform, no parallax, ≤ 300ms — asserted in both languages, and they check different things: Python that the *format* cannot express a louder floor, TypeScript that the mapping does not build one
- [x] `prefers-reduced-motion: reduce` collapses the reveal under **both** vocabularies — the v1 spec is parameterized over the harness's own motion selector rather than duplicated, so a third vocabulary is covered by existing code the day it lands
- [x] The in-page toggle still works, and still lives in the runtime rather than in an art direction

**Purity**

- [x] `motion-vocabulary.ts` contains no `typeof window`, no `process.env`, no media-query read. The v1 test that asserts this by reading its own source still passes
- [x] The renderer contains no branch on vocabulary id. Grepped: three hits, all of them prose in comments

**Human**

- [x] Watch the same scene under both vocabularies. 900ms/32px/120ms against 320ms/12px/40ms is not a subtle difference, and the harness now lets you cross them with either art direction

---

## Skipped

| Not built | Trigger |
|---|---|
| `mechanical-snap`, `physics-playful` | [11](11-range.md), after the art directions they pair with exist |
| A motion picker in the editor | [11](11-range.md). Two vocabularies do not need a UI; four do |
| Interpolating between vocabularies | v3's user control axes. A vocabulary is selected, never blended, and blending easing curves produces motion nobody authored |
| Per-block motion overrides | Not planned. `Block.motion` names an intent; the vocabulary owns every number. An override would put a duration in the scene tree and break rule 7 |

---

## Exit gate

- [x] Two motion vocabularies live in the store, byte-identical to v1's constants
- [x] Motion is a reference on the experience, defaulted from the art direction and overridable
- [x] Every vocabulary declares `slidesVariant` and `reducedMotion`
- [x] Reduced motion is proven opacity-only for every vocabulary and every intent
- [x] The renderer has no branch on vocabulary and no fifth intent
- [x] The gate is green

---

## What actually happened

**The spec's shape could not hold v1's data, by one field.** `docs/v2/art-direction-system.md` gives `MotionVocabulary` as `ease`, `easeEmphasis`, two durations, two distances, stagger, trigger — and there is nowhere in it to put `emphasize`'s **scale factor**, which is 0.96 under `cinematic-slow` and 0.99 under `editorial-restrained`. "A stage swells, a printed page does not" is one of the clearest differences between the two vocabularies, and dropping it would have made the rename change a design. `distances.emphasizeScale` is the field, and it sits with the distances because a scale is how far `emphasize` travels.

**Two shapes, and the second one is the renderer's.** The record is authored per concept — one ease, two durations — because that is how the numbers get decided, and because an authoring form with four near-identical intent blocks invites four inconsistent answers to one question. The renderer indexes by intent, because that is how a block asks. `from-motion-record.ts` is the only translation, `parallax` and `none` are derived there rather than stored, and the renderer took no change at all — which is the phase's real claim.

**`Experience.motionVocabulary` is required with no default, and that is not pedantry.** A schema default has to name one vocabulary, and naming one means every experience silently gets `cinematic-slow` motion whatever art direction it is wearing — the implicit pairing this phase exists to remove, reintroduced as a default value. "What a new experience inherits" is the art direction's `defaultMotion`, applied where experiences are created; "what this field holds when nobody said" is a different question, and the honest answer is that nobody may leave it unsaid.

**The rename needed a migration with three moving parts, not one.** Seeding the vocabularies is the easy third. `experiences.motion_vocabulary` carried `'cinematic'` on every existing row *and* as the column's server default, and the art directions seeded in 0011 named `cinematic`/`editorial` in `default_motion`. Leaving any of the three would leave a reference pointing at a vocabulary the store cannot resolve — which fails closed, correctly, on every page at once. All three are rewritten, scoped to the exact old values so a row that already names something else is not caught by a migration that was not about it.

**`default_motion` is text pointing at another table with no foreign key behind it.** That is what makes the above a real hazard rather than a hypothetical, and the two tables are seeded by two migrations. `test_motion_seed.py` asserts every art direction's default resolves; it runs on every commit rather than every deploy, which is where a constraint would have run.

### One deliberate behaviour change, named

**Reduced motion is per-vocabulary now, and `editorial-restrained` moves.** v1 had one global `REDUCED_MOTION` that both vocabularies borrowed — 200ms, on cinematic's expo curve, at cinematic's trigger. Each vocabulary declares its own duration now, and both declare 200, so **timing is unchanged for every reader**. What changes is that editorial's reduced mode fades on editorial's own easing at editorial's own trigger, instead of borrowing the other vocabulary's. That is the whole reason the phase makes the floor per-vocabulary — 200ms under `mechanical-snap` and 200ms under `physics-playful` are not the same design even when both are a bare fade — and it is asserted rather than left as a surprise.

### The e2e was deferred once, wrongly, and then done

It was written up as needing a published experience under each vocabulary — a fixture problem for phase [09](09-visual-verification.md). That was wrong: the v1 spec already runs against `/dev/primitives`, and this phase gave that harness a motion selector, so the extension was a loop and a click. Worth recording as a deferral that did not survive being looked at twice.

What the browser adds over the unit suites is a different claim, not a louder one. They assert the *floor* — opacity-only, no transform, no parallax, every vocabulary, every intent — about the objects. The e2e asserts that a real browser with the preference set gets one of those objects: a vocabulary could be perfect and the wrapper could still hand the renderer the wrong one.
