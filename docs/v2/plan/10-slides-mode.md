# Phase 10 — Slides mode

> Deferred from v1. Same tree, different playback. One scene is one slide, and the overflow mechanism is the one phase 07 already built — if slides needs its own overflow concept, one of the two designs is wrong.

**Depends on:** [07](07-reskin.md), [13](13-scene-fit.md) · **Blocks:** — · **Spec step:** 12

> **Two pieces of this phase moved to [13](13-scene-fit.md).** Viewport overflow and the scene's own frame were both scoped here, on the assumption that a fixed viewport was a slides-only condition. It is not: `fit: 'viewport'` creates it in scroll mode, four phases earlier. So `OverflowReport`-against-viewport-height and the fit shell are built there, and this phase **consumes** them. What is left here is genuinely playback: advance instead of scroll, `slidesVariant` timing, parallax off, and the padding collapse.

---

## Search

**Read first**

- [../transformations.md](../transformations.md) → "Slides mode", including the degradation table and "Overflow, again"
- [../../v1/spec.md](../../v1/spec.md) → Risk 3. "Presentation" framing sets expectations v1 could not meet, and fullscreen plus keyboard nav was the minimum that kept the word honest. This is the rest of the answer

**Grep for**

- `web/src/features/present/fullscreen.tsx` — the existing fullscreen wrapper, its arrow-key handler, the `overflow-y: auto` fix from v1's acceptance run, and the `scroll-snap-type` / `overscroll-behavior` added in [13](13-scene-fit.md). Slides mode is a second playback behaviour in this wrapper, **not a second renderer** — and it is the one place `scroll-snap-stop: always` becomes correct, because advancing is discrete
- `web/src/features/renderer/scene.tsx` — the fit shell from [13](13-scene-fit.md). A slide is a `fit: 'viewport'` scene with the padding collapsed; that is the whole geometric difference
- `api/schema/scene.py` — `Mode = Literal["scroll", "slides"]`. The field has existed since v1 and only one value has ever rendered
- `api/schema/motion.py` — `slidesVariant`, authored in phase 02. This phase reads it and adds nothing to it
- `api/features/reskin/__init__.py` — `OverflowReport`. Reused, not re-declared

**Verify externally** — nothing.

---

## Make

```
web/src/features/present/
  slides.tsx               playback: one scene, advance, no scroll
  fullscreen.tsx           chooses a playback behaviour by mode
```

### One scene is one slide

**No content changes, no second authoring pass, no auto-splitting.** A tree that reads as six scenes reads as six slides. Splitting a long scene across two slides at a machine-chosen boundary produces a break in a narratively stupid place, and the user cannot fix it without editing content they were told they would not have to.

### What changes, and it is all a lookup

| | Scroll | Slides |
|---|---|---|
| Motion trigger | 25% in viewport | on advance |
| Durations | full | ~30% shorter — a slide advance is a beat, not a journey |
| Parallax | on | off entirely |
| Scene padding | the art direction's | collapsed to fit the viewport |
| Scene fit | the AD's layout→fit table | every scene is `viewport`, unconditionally |
| Snap | `proximity` | `mandatory` + `scroll-snap-stop: always`. Both are wrong in scroll mode and both are right here, because a slide is guaranteed to fit and skipping one is a defect |
| Navigation | scroll | arrow keys, clicker, click |

The first three come from the motion vocabulary's `slidesVariant`, authored in phase 02. **Slides mode is a lookup, not a code path**, and the moment a component asks `if (mode === 'slides')` to decide a duration, that vocabulary field has been bypassed.

The padding collapse is the one genuine layout difference, and it belongs in the playback wrapper — the renderer core does not learn about modes.

### Overflow, again — and it is already built

Content that fits a tall scroll scene may not fit a fixed viewport. That check, computed against viewport height in the `render` service and reported through `OverflowReport`, is [13](13-scene-fit.md)'s work — because `fit: 'viewport'` produces the identical condition in scroll mode. **This phase adds no overflow concept and no second report type.** If slides mode appears to need one, one of the two designs is wrong.

What is different here is only the frame being measured against: a slide's frame is the viewport minus the collapsed padding, where a scroll scene's is `fitMinBlock`. Same measurement, one different input.

Three entry points became five across the release — generation, edit, reskin, scroll fit, slides — and the banner still does not say which produced it.

### `ScrollSequence` has no scroll

A scroll-driven image sequence degrades to a single representative frame, and **the editor says so when the user switches modes** rather than after they present. That primitive is phase 12; the degradation contract is recorded here because it is a mode concern.

---

## Verify

**The gate** — green.

**Playback**

- [ ] A six-scene experience presents as six slides, in order, with no content change. Assert byte-equality on `scenes` across a mode switch
- [ ] Arrow keys, click, and a presenter clicker all advance. The v1 fullscreen e2e extends to cover slides rather than being duplicated
- [ ] Motion fires on advance, not on intersection, and uses `slidesVariant`'s durations
- [ ] Parallax is off entirely in slides mode, under every vocabulary
- [ ] No component branches on `mode` to choose a duration. Greppable

**Overflow**

- [ ] Content that fits a scroll scene and not a slide **is flagged, never silently clipped**
- [ ] The report is the same type the reskin banner already renders, and **no new overflow code was written in this phase**. If any was, [13](13-scene-fit.md)'s implementation was not general enough and the fix belongs there
- [ ] A mode switch snapshots first, labelled `mode-switch`

**Accessibility**

- [ ] `prefers-reduced-motion: reduce` in slides mode collapses to opacity-only, under all vocabularies. A mode that reintroduces motion is a mode that reintroduces a WCAG 2.3.3 failure
- [ ] Keyboard navigation reaches every slide and every focusable element on it

**Human**

- [ ] Present a real experience to someone, in a room. That is the check this feature exists for and the only one that will tell you whether the padding collapse is right

---

## Skipped

| Not built | Trigger |
|---|---|
| Auto-splitting a long scene | Never. The break lands somewhere narratively stupid and the user pays for it |
| Speaker notes, presenter view | v3. They are a second surface and a second data shape, and [../../v1/spec.md](../../v1/spec.md) already answers for them |
| PDF or PPTX export | Not planned. Have a real answer ready rather than "coming soon" — the answer is a link that presents |
| Slide transitions distinct from block motion | If presenting reveals the need. The vocabulary's `slidesVariant` is the place it would go |
| Remote control from a phone | v3+ |

---

## Exit gate

- [ ] One scene is one slide, with the tree byte-identical across the switch
- [ ] Timing comes from `slidesVariant`, with no `mode` branch choosing a duration
- [ ] Parallax off, reduced motion honoured, keyboard navigation complete
- [ ] Viewport overflow reuses `OverflowReport` and the existing banner
- [ ] A mode switch snapshots first
- [ ] The gate is green
