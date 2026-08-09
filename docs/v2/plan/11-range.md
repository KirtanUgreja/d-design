# Phase 11 — Range: motion vocabularies and compare

> The two remaining motion vocabularies, the pickers, and the compare view. Twelve combinations become real here, and one of the two features in this phase is a bet that should be cut without regret if it does not earn itself.

**Depends on:** [02](02-motion-axis.md), [04](04-three-art-directions.md) · **Blocks:** — · **Spec step:** 10, 11

---

## Search

**Read first**

- [../art-direction-system.md](../art-direction-system.md) → "Motion as an independent axis", the four vocabularies and their characters
- [../transformations.md](../transformations.md) → "Compare view" and "Motion swap"
- [../spec.md](../spec.md) → the bets table. **Compare view is a bet and the first thing to cut**

**Grep for**

- `api/schema/motion.py` — the vocabulary shape from phase 02. `mechanical-snap` and `physics-playful` add no fields
- `web/src/features/renderer/motion/reveal.tsx` — the wrapper. A spring is the one thing in this phase that could tempt a change here, and see below
- `web/src/features/reskin/ad-picker.tsx` — from phase 05. The motion picker is its sibling and shares its chrome
- `web/src/app/dev/primitives/primitives-harness.tsx` — the art-direction switch added in v1. Compare view is a product-grade version of a thing that already exists as dev tooling, and reading it first is cheaper than rediscovering the layout

**Verify externally**

- Whether Motion's spring configuration expresses `physics-playful` without a second animation path. If it does not, that vocabulary is the one to cut, not the abstraction to bend

---

## Make

```
api/migrations/versions/       seed mechanical-snap, physics-playful
web/src/features/reskin/
  motion-picker.tsx            sibling of the AD picker
web/src/features/compare/
  compare-view.tsx             3 ADs, scroll-synced
  index.ts
```

### The two new vocabularies

| | Character |
|---|---|
| `mechanical-snap` | 220ms, hard cubic ease, no parallax, 60ms stagger. Feels engineered. `bold-brutalist`'s default |
| `physics-playful` | Spring-based, overshoot, 90ms stagger. Buoyant |

`bold-brutalist` was seeded in phase 04 pointing at `cinematic-slow` with a `ponytail:`. **This phase is that marker's trigger** — repoint it and delete the comment.

**`physics-playful` is the one that could break the abstraction.** A spring is not a duration and an easing curve; expressing it as one is a lie that will show. Two honest options, in order of preference:

1. Approximate it as a cubic-bézier with overshoot and accept that it is not a real spring. The vocabulary shape survives, the motion is 90% there, and nobody outside this file knows
2. Add a `spring { stiffness, damping, mass }` variant to `MotionIntentDef` as a **discriminated union** with the existing shape, so the renderer reads one field or the other with no branch on vocabulary id

What is not an option is a code path in `reveal.tsx` that checks which vocabulary it received. If neither option above works, **cut `physics-playful`** and ship three vocabularies. Nine combinations still make the argument.

### The pickers

Two controls, side by side in the editor toolbar — space [../../design/app.md](../../design/app.md) already reserves. The art direction's `defaultMotion` is preselected; the other three are available and unrecommended.

`bold-brutalist` + `cinematic-slow` is a real aesthetic choice, just not one to put on the default path. The surface stays curated by ordering and by the default, never by hiding options.

**Swapping motion changes no layout, produces no overflow, and needs no snapshot beyond ordinary history.** It is the cheap axis, and building it as a smaller version of reskin rather than as reskin-with-a-flag is what keeps it cheap.

### Compare view — and how to cut it

The same experience under three art directions, side by side, scroll-synced. Renders each one's hero scene at full fidelity; scrolling one scrolls all; clicking one applies it, which runs the reskin flow, transition and all.

Users decide with their eyes rather than by reading art-direction names. That is the argument.

**It is a bet.** Users may decide from thumbnails and never open it. It is cheap enough to try and it is the first thing to cut — so build it *last within this phase*, keep it in its own feature folder with one public export, and make deleting it a `git rm` of one directory plus one route.

Three live renderers on one page is also the most expensive thing in v2 per pixel shown. If it is slow, render the hero scene only and do not be clever about it.

---

## Verify

**The gate** — green.

**Vocabularies**

- [ ] Four vocabularies in the store, each with `slidesVariant` and `reducedMotion`
- [ ] All four pass the linter's motion bounds — 120ms to 1400ms, reduced motion opacity-only and ≤ 300ms
- [ ] `bold-brutalist` defaults to `mechanical-snap`, and the phase 04 `ponytail:` is gone
- [ ] `reveal.tsx` has no branch on vocabulary id. If `physics-playful` shipped, it shipped as a discriminated union the renderer reads generically — or it did not ship

**The matrix**

- [ ] **3 art directions × 4 vocabularies × 2 modes × 5 golden experiences = 120 renders.** All valid, no crashes, overflow correctly reported. This is the reskin matrix from [../spec.md](../spec.md) → Verification and it is the closest thing v2 has to a single proof
- [ ] `prefers-reduced-motion: reduce` collapses motion in every one of the 24 axis combinations

**Pickers**

- [ ] Changing motion changes no layout and produces no overflow entries
- [ ] An explicit motion choice survives a reskin; an unset one takes the new art direction's default

**Compare**

- [ ] Three panes render the same experience under three art directions, scroll-synced
- [ ] Clicking one runs the full reskin flow — snapshot, swap, overflow, transition
- [ ] Deleting `web/src/features/compare/` and its route leaves everything else green. **Assert this by actually doing it once**, because a bet you cannot cut is not a bet

**Human**

- [ ] Watch one scene under all four vocabularies. If two are indistinguishable, one of them is not worth the row in the table
- [ ] Open compare view and decide whether you would use it. This is a bet, and you are the only user there is

---

## Skipped

| Not built | Trigger |
|---|---|
| Interpolating between vocabularies | v3's motion-energy control axis. A vocabulary is selected, never blended |
| A fifth vocabulary | Real demand. Four is already twelve combinations from seven artifacts |
| Compare across motion vocabularies | Motion does not read from a still frame. Compare is a visual-style tool |
| Thumbnails instead of live renders | If compare survives and is slow. That is the cheaper design and it may be the better one |

---

## Exit gate

- [ ] Four motion vocabularies, all linted, all with slides and reduced variants
- [ ] `physics-playful` shipped without a renderer branch, or was cut and recorded
- [ ] The 120-render matrix passes
- [ ] Motion and art-direction pickers are both in the toolbar, curated by default and not by omission
- [ ] Compare view works and is provably deletable in one commit
- [ ] The gate is green
