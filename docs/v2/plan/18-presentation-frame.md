# Phase 18 — The presentation frame

> A slide fills the screen edge to edge and is guaranteed to work from 4:3 to 21:9. Fluid tokens stop being driven by viewport width and start being driven by the smaller axis of the stage. One unit change, one CSS property, zero branches.

**Depends on:** [00](00-foundations.md), [13](13-scene-fit.md) · **Blocks:** [10](10-slides-mode.md), [19](19-presenter-view.md), [20](20-offline-and-export.md) · **Spec step:** presentation delta

This is the first phase of the presentation pivot and everything else in it waits here. Read [../presentation.md](../presentation.md) → "The frame" before starting; this file implements that section and does not restate its argument.

---

## Search

**Read first**

- [../presentation.md](../presentation.md) → "The frame", including the overflow table with real numbers. The 21:9 row is the defect this phase exists for
- [13-scene-fit.md](13-scene-fit.md) → the `fit` shell and `OverflowReport`. This phase adds a second *input* to that measurement and **no new overflow concept**
- [../art-direction-system.md](../art-direction-system.md) → the `$extensions` payload, where `Unit` and `ClampTriple` live

**Grep for**

- `api/schema/art_direction.py` → `Unit = Literal["px", "rem", "ch", "vw", "vh", "svh", "%"]`. This is the line the phase turns on. `ClampTriple` and `Length` are immediately below it and do not change shape
- `api/schema/fixtures/art_directions.json` → every `"unit": "vw"` inside a `preferred`. These are the values being re-authored, in all three art directions
- `web/src/features/renderer/scene.tsx` → the fit shell from [13](13-scene-fit.md). The stage containment declaration goes on the surface *above* this, not in it
- `web/src/features/art-direction/to-css-vars.ts` → where a `ClampTriple` becomes `clamp(...)`. A new unit must serialise with no special case; if it needs one, `Unit` was modelled wrong
- `api/features/art_direction/lint.py` → the linter gains the range check described below

**Verify externally**

- Container query units (`cqmin`, `cqw`, `cqh`, `cqmax`) and `container-type: size` — Baseline support, and specifically whether `container-type: size` on a full-screen element has any layout cost worth knowing about
- Confirm `cqmin` resolves against the **nearest size container**, and what it falls back to when no container is declared. The fallback behaviour decides whether an un-staged render (a bare `/dev/primitives` page) silently produces different numbers

---

## Make

```
api/schema/art_direction.py        Unit gains cqmin/cqw/cqh/cqmax
api/features/art_direction/lint.py aspect-range rule
api/features/present/
  preflight.py                     four-ratio check, one OverflowReport per ratio
web/src/features/present/
  stage.tsx                        the size container. Not in renderer/
```

### The unit change

`Unit` gains `cqmin`, `cqw`, `cqh`, `cqmax`. Nothing is removed in this phase — `vw` and `svh` stay legal so the migration is not a big-bang, and the linter is what makes the new units mandatory rather than the type system.

**Every `preferred` value in every art direction is re-authored from `vw` to `cqmin`.** The `min` and `max` legs of each clamp are already absolute (`rem`) and do not move. The numbers themselves carry over unchanged — `8vw` becomes `8cqmin` — because on a 4:3 and 16:10 stage the two are near-identical, and those are the ratios the three art directions were designed against. **The values were never wrong; the axis they were measured on was.**

### The stage

One element declares `container-type: size` and every fluid token below it resolves against the frame it is actually inside.

It lives in `present/`, **not** in `renderer/`. The renderer core does not learn what a stage is, does not learn what mode it is in, and does not gain a prop — rule 6 holds. A slide stage, an editor canvas, a `render` service viewport and the presenter's next-slide preview are four different surfaces that each declare containment and each get correct numbers for free. That is the entire argument for container units over `vmin`, and it is worth re-reading if the `vmin` shortcut starts looking attractive during the build: `vmin` is three lines shorter and wrong in three of the four surfaces.

### The four-ratio preflight

| Ratio | Pixels | What it stands for |
|---|---|---|
| 4:3 | 1440×1080 | old conference-room projectors |
| 16:10 | 1680×1050 | most laptops |
| 16:9 | 1920×1080 | projectors, TVs, and the PDF export size |
| 21:9 | 1920×823 | hall LED walls and ultrawide monitors |

The `render` service loads the deck once and measures at each viewport. **Reuse `OverflowReport` exactly** — same type, same banner, same shorten-with-AI affordance, four results instead of one. The report gains a ratio label and nothing else.

Overflow at any of the four is a **defect**, not a warning to scroll past. In a scrolling handout a tall scene grows; on a slide there is nowhere to grow, so the same measurement carries a different consequence and the banner says so.

### The linter rule

An art direction whose `preferred` values are width-driven cannot keep the guarantee, so the linter stops accepting them:

- Every `ClampTriple.preferred` must use `cqmin` (or an absolute unit, for a deliberately fixed value). `vw`, `vh` and `svh` in a `preferred` are a **hard failure** with a message naming this phase
- The `min` leg must be small enough that a 21:9 stage does not floor into overflow — the clamp's floor is what actually bites at 823px of height, and an art direction can pass every other check and still be undeliverable because its `min` is too tall

---

## Verify

**The gate** — green, including the schema regenerating with no diff.

**The unit change**

- [ ] `cqmin` serialises through `to-css-vars.ts` with no branch. If it needed one, `Unit` was modelled wrong and the fix is there
- [ ] All three art directions re-authored, and `/dev/primitives` at 16:10 is **visually unchanged** from before the phase. This is the check that proves the numbers carried over rather than being retuned by accident
- [ ] No `vw`, `vh` or `svh` survives in any `preferred` in `art_directions.json`. Greppable

**The guarantee**

- [ ] The eight-scene fixture tree renders with zero overflow at all four ratios, under all three art directions. That is 96 measurements and it is the phase's actual deliverable
- [ ] A deliberately over-long headline overflows at 21:9 and is **reported, not clipped**
- [ ] The same headline at 4:3 does not report — the check has to be able to say no, or it is not a check
- [ ] No new overflow type was declared. Greppable against [13](13-scene-fit.md)'s implementation

**Purity**

- [ ] `renderer/` gained no prop, no `mode`, no container declaration and no branch. Rule 6 and `scripts/checks/invariants.sh`
- [ ] The editor canvas — a stage smaller than the viewport — produces type sized to the canvas, not to the window. This is the case `vmin` would have got wrong and the reason the phase chose container units

**Human**

- [ ] Open the same deck on a laptop and on a 21:9 monitor, full screen, and look at both. The preflight can only prove nothing overflows; whether the 21:9 version is *composed* is a judgement, and if it reads as a 16:9 slide with air on the sides, [17](17-composition.md) has work this phase cannot do

---

## Skipped

| Not built | Trigger |
|---|---|
| Fixed 16:9 canvas with letterboxing | Only as a retreat. If the four-ratio guarantee proves unkeepable in real rooms, this is the fallback — and taking it is a deliberate decision, not a drift ([../presentation.md](../presentation.md) → Risks) |
| Per-art-direction aspect ranges | An AD that only works at 16:9 breaks the reskin guarantee. Any AD must work with any deck |
| Ratios beyond 21:9 — 32:9, phones | 32:9 is rare enough to flag rather than support. Portrait is a different product |
| Removing `vw`/`svh` from `Unit` | After all three ADs are migrated and the linter has been green for a release. Removing a unit is a schema break for no gain while the linter already forbids it |
| Letting the user choose a target ratio | The guarantee is that all four work. A picker would be an admission it does not |

---

## Exit gate

- [ ] `Unit` carries the container units and the schema regenerates clean
- [ ] All three art directions use `cqmin` in every `preferred`, and 16:10 is visually unchanged
- [ ] The stage lives in `present/` and `renderer/` is untouched by this phase
- [ ] Zero overflow across 4 ratios × 3 art directions × the fixture tree
- [ ] The linter hard-fails a width-driven `preferred`
- [ ] `OverflowReport` was reused, not re-declared
- [ ] The gate is green
