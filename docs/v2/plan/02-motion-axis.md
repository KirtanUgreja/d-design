# Phase 02 — Motion as an independent axis

> Motion stops belonging to an art direction and becomes a thing you choose. Three art directions × four vocabularies = twelve combinations from seven authored artifacts, and that ratio is the entire argument.

**Depends on:** [01](01-ad-format.md) · **Blocks:** [04](04-three-art-directions.md), [11](11-range.md) · **Spec step:** 2

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

- [ ] `cinematic-slow` and `editorial-restrained` produce byte-identical CSS to v1's constants
- [ ] Every one of the 2 × 2 art-direction/vocabulary combinations renders the `full` fixture without a crash and without a layout change attributable to motion
- [ ] An experience with an explicit motion choice keeps it across a reskin; one without picks up the new art direction's default
- [ ] `staggerDelayMs` still caps at 5 siblings, computed in one place

**Reduced motion**

- [ ] Every vocabulary's `reducedMotion` is opacity-only, no transform, no parallax, ≤ 300ms
- [ ] `prefers-reduced-motion: reduce` collapses all four intents under both vocabularies — the v1 e2e extends to cover the second one rather than being duplicated
- [ ] The in-page toggle still works, and still lives in the runtime rather than in an art direction

**Purity**

- [ ] `motion-vocabulary.ts` contains no `typeof window`, no `process.env`, no media-query read. The v1 test that asserts this by reading its own source still passes
- [ ] The renderer contains no branch on vocabulary id. Greppable, and worth grepping

**Human**

- [ ] Watch the same scene under both vocabularies. If you cannot tell them apart, either the vocabularies are too close or the renderer is ignoring one of them — and both are worth knowing before three more arrive

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

- [ ] Two motion vocabularies live in the store, byte-identical to v1's constants
- [ ] Motion is a reference on the experience, defaulted from the art direction and overridable
- [ ] Every vocabulary declares `slidesVariant` and `reducedMotion`
- [ ] Reduced motion is proven opacity-only for every vocabulary and every intent
- [ ] The renderer has no branch on vocabulary and no fifth intent
- [ ] The gate is green
