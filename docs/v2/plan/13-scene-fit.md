# Phase 13 — The scene as a stage

> A scene is currently as tall as whatever the model wrote inside it, so two of them share the viewport and neither one is composed. This phase gives a scene a floor, a centre, and a snap point — and it is the phase that decides whether the output reads as slides or as a scrolling document.

**Depends on:** [01](01-ad-format.md) · **Blocks:** [04](04-three-art-directions.md), [10](10-slides-mode.md), [17](17-composition.md) · **Spec step:** delta — see [../spec.md](../spec.md) → "Composition deltas"

---

## The defect, precisely

`web/src/features/renderer/scene.tsx` renders:

```tsx
<section id={`scene-${scene.id}`} style={{ position: 'relative' }}>
```

There is no `min-block-size`, no snap point, and no vertical placement. A scene is exactly as tall as its padding plus its content — so a hero with four words is roughly 40vh tall and a proof scene with a list is 130vh, and at any scroll position the viewport is showing the bottom of one scene and the top of the next. `present/fullscreen.tsx` calls `scrollIntoView` on the section, which aligns its *top* to the viewport top and then leaves the next scene's first 30% visible below it.

**This is not a polish item.** Every compositional judgement an art direction makes — negative space, where the eye lands, whether a headline is the only thing on screen — assumes the scene owns the frame. It never has. It is also why the deferred work in [17](17-composition.md) cannot start first: composing inside a box of unknown height is composing nothing.

---

## Search

**Read first**

- [../../v1/art-direction.md](../../v1/art-direction.md) → "Rhythm". `--scene-padding-y: clamp(6rem, 14vh, 12rem)` and *"Scenes are generously tall"* — the intent was always a scene that owns the frame; padding was the only mechanism available and it does not survive short content
- [../transformations.md](../transformations.md) → "Overflow". A scene that will not fit is reported, never clipped, and this phase is the first place that can happen in **scroll** mode rather than only in slides
- [../../v1/spec.md](../../v1/spec.md) → Risk 3. Fullscreen and arrow keys were the minimum that kept the word "presentation" honest. A frame that holds one scene is the rest of it

**Grep for**

- `web/src/features/renderer/scene.tsx` — the `<section>` above, and `SCENE_PADDING_BLOCK` / `SCENE_PADDING_INLINE`. The fit shell goes here, on the element that already exists
- `web/src/features/renderer/tokens.ts` — `SCENE_PADDING_BLOCK`, `MEASURE`, `CONTENT_MAX`. New token accessors join these; **do not add a second token→string path**, `to-css-vars.ts` is still the only one
- `web/src/features/art-direction/art-direction.ts` → `interface Rhythm`. `fit` is a rhythm token, not a new group
- `web/src/features/present/fullscreen.tsx` — `goTo`, `scrollIntoView`, and the `blockSize: '100%', overflowY: 'auto'` fix from the v1 acceptance run. **The scroll container lives here**, which is where `scroll-snap-type` belongs
- `web/src/features/renderer/layouts/full-bleed.tsx` — the one layout that opts out of the padding shell. It does **not** opt out of the fit shell; bleeding to the edges and filling the frame are different properties
- `api/schema/scene.py` → `SlotProps.height: Literal["viewport", "auto"]`. The concept already exists on one block; this phase is the same idea at scene level, and the two should not drift into two vocabularies

**Verify externally**

- `svh` / `lvh` / `dvh` support and behaviour. All three shipped across Chrome, Safari and Firefox in 2023 and are above 90% global as of 2026 — but the choice between them is a design decision, not a support one, and it is made below

---

## Make

```
web/src/features/art-direction/
  art-direction.ts        + SceneFit, Rhythm.fit, Rhythm.fitMinBlock
  cinematic-dark.ts       + the fit table
  editorial-light.ts      + the fit table
  to-css-vars.ts          + --scene-min-block, --scene-place, --scene-scroll-margin
web/src/features/renderer/
  tokens.ts               + SCENE_MIN_BLOCK, SCENE_PLACE, SCENE_SCROLL_MARGIN
  scene.tsx               the fit shell
web/src/features/present/
  fullscreen.tsx          scroll-snap-type, overscroll-behavior, reduced-motion scroll
api/schema/art_direction.py   fit table in the AD record (phase 01's format)
api/features/reskin/
  __init__.py             + viewport overflow, reused by phase 10 rather than rebuilt
```

### 1. `fit` is derived from the layout, by the art direction

The tempting shape is a `fit` field on `Scene`. **It is the wrong shape and it violates rule 7** — how much of the frame a scene occupies is a presentational decision, and the AI does not get one. It is also the wrong shape for reskin: a scene pinned to `viewport` by the model would stay pinned under an art direction whose whole character is that proof scenes run long.

So the art direction owns a lookup from something the AI *does* write:

```ts
type SceneFit = 'viewport' | 'content';

interface Rhythm {
  // …existing
  fit: Record<Layout, SceneFit>;
  fitMinBlock: Length;      // the floor a `viewport` scene gets. 100svh.
  fitPlace: 'center' | 'start' | 'end';
}
```

`cinematic-dark` sets every layout to `viewport` — deep space, one beat per screen, and it is the art direction the spec calls forgiving of sparse content. `editorial-light` sets `full-bleed` and `centered` to `viewport` and lets `stack` and `grid` run at content height, because a printed spread that pads a spec table to 100vh looks like a spec table with a bug. `bold-brutalist` will want all six pinned. **Three different answers from one table and no branch anywhere** — which is the test that this is a token and not a feature.

The AI writes `layout`. The art direction turns that into a frame. Nothing new reaches the schema.

### 2. `100svh`, and specifically not `vh` or `dvh`

| | Why not |
|---|---|
| `100vh` | On mobile it is the *largest* viewport — the one with the browser chrome retracted. A full-height scene overflows by the height of the URL bar on first paint, which is the same bleed defect in a different costume |
| `100dvh` | Correct at every instant and therefore recalculating at every instant. The browser UI hiding and showing on scroll resizes every scene in the document mid-scroll, and a snap point that moves while you are scrolling toward it is worse than no snap point |
| **`100svh`** | The *small* viewport — chrome expanded. Stable for the whole scroll, and the cost is a strip of empty ground at the bottom once the URL bar retracts, which on a full-bleed art direction is invisible |

`svh` is the right default for exactly the reason this product is unusual: a scene is a **stage**, and a stage that changes size while the audience is looking at it is not one. Write `vh` first and `svh` second so a browser that does not know the unit still gets a floor.

Keep it a token (`fitMinBlock`) rather than a constant. An art direction that wants 90svh with a deliberate sliver of the next scene showing is making a legitimate choice, and the moment that is hardcoded it is our choice for everyone.

### 3. `min-block-size`, never `block-size`

The floor is a floor. A scene whose content is taller than the frame **grows**, and then it is reported — it is never clipped and never scrolls internally. Internal scroll inside a scene inside a scrolling page is the single worst outcome available here, and `block-size: 100svh` plus `overflow: auto` is how products arrive at it by accident.

### 4. Placement is the other half, and it is the half that looks designed

A four-word hero in a 100svh box with `place-content: start` is a headline stuck to the ceiling of an empty room. Half the perceived quality of this change is `place-content: center` on the fit shell, so short content sits in the optical middle of the frame with equal air above and below. That is `fitPlace`, and it is a token because `bold-brutalist` will want `end` — type jammed to the baseline is most of what that art direction is.

Optical, not mathematical: the frame is centred against the padding box, so the AD's `scenePaddingY` still sets the minimum air. A scene at exactly the frame height is unaffected.

### 5. Snap: `proximity` on the container, `align: start` on the scene

Two properties, two owners, and the split matters:

| | Where | Why there |
|---|---|---|
| `scroll-snap-align: start` | the `<section>`, in the renderer core | A property of a scene. Valid in the browser, in the app server's HTML, and in the render service — no mode, no environment read, rule 6 intact |
| `scroll-snap-type: y proximity` | the scroll container, in `present/fullscreen.tsx` | A property of a *playback surface*. The renderer does not know it is inside one |

**`proximity`, not `mandatory`, and this is the decision most likely to be reversed by someone who has not read this paragraph.** Under `mandatory`, a scene taller than the viewport becomes unreadable: the browser snaps to the top of that scene or the top of the next one, and the middle of a long scene cannot be held on screen. Scene heights in this product are not predictable — that is the entire premise of the overflow report — so `mandatory` is a promise the content cannot keep. Under `proximity` a short scene snaps cleanly and a long scene simply does not, because you are never near a snap point while reading its middle. It degrades in the right direction on its own, with no measurement and no JavaScript.

`scroll-snap-stop: always` is **not** used in scroll mode. It fights fling-scrolling, WebKit does not respect it during momentum scroll, and its job — never skipping a scene — belongs to slides mode, where advancing is discrete by construction.

### 6. `scroll-margin-block-start`, and the fixed chrome

`goTo` in `present/fullscreen.tsx` aligns a scene's top edge to the viewport's top edge. The present/motion control pill is `position: fixed` at the top of the same viewport, so the first line of every scene navigated to by arrow key lands underneath it. `scroll-margin-block-start` on the section fixes both `scrollIntoView` and the snap position with one declaration, and it is a token (`--scene-scroll-margin`) because the chrome's height is not the renderer's business.

### 7. `overscroll-behavior: contain` on the scroll container

Scrolling past the last scene currently chains to the document behind the fullscreen element. Contain it. One line, and it is the difference between the end of a presentation and a bounce.

### 8. Smooth scroll is motion, and motion is opt-out

`scrollIntoView({ behavior: 'smooth' })` is unconditional today. Under `prefers-reduced-motion: reduce` it becomes `'auto'` — a jump. Scroll-triggered movement is exactly what WCAG 2.3.3 covers and what [../../v1/art-direction.md](../../v1/art-direction.md) → "Reduced motion is a design requirement here" already commits to; the reveal animations honour it and the navigation does not, which is the half-wired state that reads as a bug to the people it affects. The in-page toggle governs it too, not just the media query.

### 9. Viewport overflow arrives here, not in phase 10

[10](10-slides-mode.md) was going to compute overflow against viewport height as part of slides mode. It moves here, because `fit: 'viewport'` creates the same condition in **scroll** mode and creates it four phases earlier. Same `OverflowReport`, same banner, same shorten-with-AI affordance — a fourth entry point alongside generation, edit and reskin, and the banner still does not say which produced it.

Measuring against a viewport means a layout exists, which means the `render` service from [00](00-foundations.md). This is its first customer, ahead of the critic.

---

## Verify

**The gate** — green.

**Fit**

- [ ] Every scene under `cinematic-dark` occupies at least the frame. Screenshot any scroll position with `scroll-snap` disabled and assert at most one scene boundary is visible in a 100svh window, for all 5 golden experiences
- [ ] A scene with four words is vertically centred, with air above and below, not pinned to the top
- [ ] A scene with more content than the frame **grows**. Assert `scrollHeight === clientHeight` on every `<section>` — a scene that scrolls internally is a hard failure
- [ ] `editorial-light`'s `stack` and `grid` scenes are content-height and do not pad to the frame. Two art directions, two answers, **one code path** — grep `renderer/` for `svh`, `100vh`, and `fit` and find only token reads
- [ ] The `hostile` fixture's unbreakable-run headline still does not overflow the inline axis inside a fit shell

**Snap and navigation**

- [ ] Arrow keys land each scene flush against the top of the frame with the control pill clear of the content
- [ ] A scene taller than the viewport can be scrolled through and held at its middle. This is the `mandatory` trap and it must be tested with a real over-long scene, not asserted
- [ ] `scroll-snap-type` appears only in `present/`, `scroll-snap-align` only in `renderer/`. Greppable, and it is the rule-6 check for this phase
- [ ] Scrolling past the last scene does not chain to the document behind it
- [ ] `prefers-reduced-motion: reduce` makes arrow-key navigation jump rather than glide, under both the media query and the in-page toggle

**Overflow**

- [ ] A scene whose content exceeds the frame produces an `OverflowReport` entry in **scroll** mode
- [ ] The report is the same type the reskin banner renders. If slides mode later needs a second type, one of the two designs is wrong
- [ ] Content is never clipped and never hidden. Assert against the DOM, not against a screenshot

**Cross-surface**

- [ ] The embed at a small iframe size gets a frame relative to the iframe, not the page. `svh` resolves against the iframe's own viewport; confirm rather than assume
- [ ] The `render` service screenshots at a declared viewport size, and the size is recorded with the screenshot. A critic looking at a scene composed for an unknown frame is looking at nothing
- [ ] The published page and the editor canvas agree. The editor canvas is not a viewport, and a fit shell inside it needs a declared frame or every scene is 100svh of the *editor's* window

**Human**

- [ ] Scroll a real 8-scene experience end to end on a laptop and on a phone. The check is whether it reads as a sequence of composed frames or as a long page with big gaps, and no assertion above answers it

---

## Skipped

| Not built | Trigger |
|---|---|
| `scroll-snap-type: mandatory` | Never, while scene height is content-dependent. If a future release guarantees every scene fits, revisit |
| `scroll-snap-stop: always` | Slides mode, where advancing is discrete. In scroll mode it fights the scroll it is meant to help |
| Sticky/pinned scenes — a scene held while its content advances | A real scene needs it. It is the award-site move and it is also a second playback concept; `ScrollSequence` in [12](12-primitives.md) is the one place the need is already known, and it brings its own answer |
| A per-scene `fit` override in the editor | The AD's table is the answer until a user asks for the exception. If they do, it is an editor-side override on the experience, never a field the AI writes |
| Snapping in the editor canvas | The canvas is an editing surface, not a playback one |
| Horizontal scroll modes | Not in v2 |

---

## Exit gate

- [ ] Every art direction declares a layout→fit table, and the renderer reads it with no branch
- [ ] A `viewport` scene has a `min-block-size` floor in `svh`, is placed by a token, and grows rather than clipping
- [ ] At most one scene boundary is visible in a frame, across all 5 golden experiences and all art directions
- [ ] `proximity` snapping, with a tall scene still fully readable
- [ ] Arrow-key navigation lands flush and respects reduced motion
- [ ] Viewport overflow reports through the existing `OverflowReport`, in scroll mode
- [ ] The gate is green
