# Phase 10 — Presentation playback

> The default. One scene is one slide, advance instead of scroll, timing from `slidesVariant`, padding collapsed to the stage. The frame this plays inside is [18](18-presentation-frame.md)'s and the overflow mechanism is [13](13-scene-fit.md)'s — **this phase adds neither.**

**Depends on:** [13](13-scene-fit.md), [18](18-presentation-frame.md) · **Blocks:** [19](19-presenter-view.md), [20](20-offline-and-export.md), [22](22-deck-length.md), [23](23-phone-remote.md) · **Spec step:** 12

> **This phase changed meaning on 2026-08-10.** It was written as *"deferred from v1 — same tree, different playback"*: a mode you could switch into, built late, after reskin. It is now **the product's default playback**, and the scrolling page it was a mode of is the secondary view. See [../presentation.md](../presentation.md).
>
> The build is almost exactly what it was. What changed is the position, the ordering, and one consequence: **overflow on a slide is a defect rather than growth**, because there is nowhere to grow. Same measurement, different verdict.
>
> **Two pieces of this phase moved to [13](13-scene-fit.md)** when it was written, and that split still holds: viewport overflow and the scene's own frame are built there because `fit: 'viewport'` creates the identical condition in the handout view. A third piece — the aspect-range guarantee — is [18](18-presentation-frame.md). This phase consumes all three.

---

## Search

**Read first**

- [../presentation.md](../presentation.md) → "Playback", which is the table this phase implements, and "What does not change", which is most of the system
- [../transformations.md](../transformations.md) → "Presentation and the handout", including the degradation table
- [18](18-presentation-frame.md) → the stage and its containment. A slide is a stage-sized scene and this phase does not re-derive that
- [../../v1/spec.md](../../v1/spec.md) → Risk 3. *"'Presentation' framing sets expectations v1 won't meet."* This phase, plus [19](19-presenter-view.md) and [20](20-offline-and-export.md), is the rest of that answer

**Grep for**

- `web/src/features/present/fullscreen.tsx` — the existing fullscreen wrapper, its arrow-key handler, the `overflow-y: auto` fix from v1's acceptance run, and the `scroll-snap-type` / `overscroll-behavior` from [13](13-scene-fit.md). Presentation is a second playback behaviour **in this wrapper**, not a second renderer — and the one place `scroll-snap-stop: always` is correct, because advancing is discrete
- `web/src/features/present/stage.tsx` — [18](18-presentation-frame.md)'s size container. The slide is inside it
- `web/src/features/renderer/scene.tsx` — the fit shell. A slide is a `fit: 'viewport'` scene with the padding collapsed; that is the whole geometric difference
- `api/schema/scene.py` — `Mode = Literal["scroll", "slides"]`. The field has existed since v1; this phase makes `slides` the default for new experiences and leaves existing rows alone
- `api/schema/motion.py` — `slidesVariant`, authored in phase 02. This phase reads it and adds nothing to it
- `api/features/reskin/__init__.py` — `OverflowReport`. Reused, not re-declared

**Verify externally** — nothing. [18](18-presentation-frame.md) did the platform checks this phase depends on.

---

## Make

```
web/src/features/present/
  slides.tsx               playback: one slide, advance, no scroll
  fullscreen.tsx           chooses a playback behaviour by mode
```

### One scene is one slide

**No content changes, no second authoring pass, no auto-splitting.** A tree that reads as six scenes reads as six slides. Splitting a long scene at a machine-chosen boundary produces a break in a narratively stupid place, and the user cannot fix it without editing content they were told they would not have to.

### What changes, and it is all a lookup

| | Handout (scroll) | **Presentation (default)** |
|---|---|---|
| Motion trigger | 25% in viewport | on advance |
| Durations | full | ~30% shorter — an advance is a beat, not a journey |
| Parallax | on | off entirely |
| Scene padding | the art direction's | collapsed to the stage |
| Scene fit | the AD's layout→fit table | every slide is the stage, unconditionally |
| Snap | `proximity` | `mandatory` + `scroll-snap-stop: always`. Both wrong in the handout and both right here, because a slide is guaranteed to fit and skipping one is a defect |
| Navigation | scroll | arrow keys, click, clicker, and later a phone |

The first three come from `slidesVariant`, authored in phase 02. **Playback is a lookup, not a code path**, and the moment a component asks `if (mode === 'slides')` to decide a duration, that vocabulary field has been bypassed.

The padding collapse is the one genuine layout difference, and it belongs in the playback wrapper. The renderer core does not learn about modes.

### The default flips

New experiences are created as `slides`. The shared link opens as a deck: one slide, advance controls, a fullscreen affordance. The handout view is reachable and is not the default anywhere.

**Existing rows are not migrated.** Anything already published as `scroll` stays as it was — [../transformations.md](../transformations.md) pins presentation-affecting choices at publish for the same reason it pins the art direction, and a live deck that changes how it plays overnight is the failure that rule exists to prevent.

### Overflow means something different here

Content that fits a tall handout scene may not fit a stage. That check — computed against the stage in the `render` service, reported through `OverflowReport`, and run at four aspect ratios — is [13](13-scene-fit.md)'s and [18](18-presentation-frame.md)'s work. **This phase adds no overflow concept and no second report type.**

What it adds is the verdict. In the handout a tall scene grows: ugly, survivable. On a slide there is nowhere to grow, so overflow is a blocking defect and the banner says so in those terms.

### `ScrollSequence` has no scroll

A scroll-driven image sequence degrades to a single representative frame, and **the editor says so when the user switches modes**, not after they present. That primitive is phase 12; the degradation contract is recorded here because it is a mode concern.

---

## Verify

**The gate** — green.

**Playback**

- [ ] A six-scene experience presents as six slides, in order, with no content change. Assert byte-equality on `scenes` across a mode switch
- [ ] Arrow keys, click, and a presenter clicker all advance. The v1 fullscreen e2e extends to cover this rather than being duplicated
- [ ] Motion fires on advance, not on intersection, and uses `slidesVariant`'s durations
- [ ] Parallax is off entirely, under every vocabulary
- [ ] No component branches on `mode` to choose a duration. Greppable

**The default**

- [ ] A new experience is created as `slides`
- [ ] A shared link opens as a deck, not as a scrolling page
- [ ] An experience already published as `scroll` is untouched and still renders as it did

**Overflow**

- [ ] Content that fits the handout and not a slide **is flagged, never silently clipped**, and the banner calls it a defect rather than a warning
- [ ] The report is the same type the reskin banner already renders, and **no new overflow code was written in this phase**. If any was, [13](13-scene-fit.md) or [18](18-presentation-frame.md) was not general enough and the fix belongs there
- [ ] A mode switch snapshots first, labelled `mode-switch`

**Accessibility**

- [ ] `prefers-reduced-motion: reduce` collapses to opacity-only, under all vocabularies. A mode that reintroduces motion reintroduces a WCAG 2.3.3 failure
- [ ] Keyboard navigation reaches every slide and every focusable element on it

**Human**

- [ ] Present a real deck to someone, in a room, on an external display. That is the check this feature exists for and the only one that will tell you whether the padding collapse is right

---

## Skipped

| Not built | Trigger |
|---|---|
| Auto-splitting a long scene | Never. The break lands somewhere narratively stupid and the user pays for it |
| Speaker notes and presenter view | [19](19-presenter-view.md). They are core now, not deferred — just not this phase |
| PDF and offline | [20](20-offline-and-export.md) |
| Slide transitions distinct from block motion | If presenting reveals the need. `slidesVariant` is where it would go |
| Migrating existing `scroll` experiences | Never automatically. Published output does not change under its author |
| Removing scroll mode | Not planned. It is the handout and it costs nothing ([../presentation.md](../presentation.md) → "The handout") |

---

## Exit gate

- [ ] One scene is one slide, tree byte-identical across the switch
- [ ] Timing from `slidesVariant`, with no `mode` branch choosing a duration
- [ ] Slides is the default for new experiences; the shared link opens as a deck
- [ ] Already-published `scroll` experiences are untouched
- [ ] Parallax off, reduced motion honoured, keyboard navigation complete
- [ ] Overflow reuses `OverflowReport` and reports as a defect
- [ ] A mode switch snapshots first
- [ ] The gate is green
