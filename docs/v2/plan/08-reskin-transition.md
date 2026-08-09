# Phase 08 — The reskin transition

> Where the delight budget goes. The platform now does the hard part, so this phase is a naming problem wearing an animation problem's reputation.

**Depends on:** [07](07-reskin.md) · **Blocks:** — · **Spec step:** 8

---

## Search

**Read first**

- [../transformations.md](../transformations.md) → "The transition — where the delight budget goes", including the three remaining constraints
- [../spec.md](../spec.md) → "Platform reality", the View Transitions row, and Risk 2, which is **retired** — an earlier draft specified a hand-rolled FLIP loop and the platform absorbed it

**Grep for**

- `web/src/features/renderer/motion/reveal.tsx` — how motion is applied today, and the `data-block-id` already stamped on every wrapper. That attribute is the name source; do not invent a second identity scheme
- `web/src/features/present/fullscreen.tsx` — the wrapper that already branches on the environment. The reduced-motion branch for this belongs in that layer, not in the core
- `next.config.ts` — `reactCompiler` is on. A `startTransition` around a state update is exactly the shape it is good at, and nothing here needs a memo written by hand

**Verify externally**

- That `document.startViewTransition` is present in the browsers you care about and simply **absent** elsewhere. The absence is the fallback; confirm it rather than assuming, because "absent" and "present but broken" need different code and only one of them needs none

---

## Make

```
web/src/features/reskin/
  reskin-transition.tsx     the ViewTransition wrapper and the name scoping
  use-viewport-blocks.ts    which block ids are on screen right now
```

### The whole mechanism

```tsx
startTransition(() => setArtDirection(next))
```

A reskin is a same-document DOM state change, which is precisely what the API is for: the browser snapshots the old state, snapshots the new one, and animates between them — **including the layout shift that FLIP existed to compute**. React 19.2's `<ViewTransition>` handles coordinating the browser's snapshot with React's render cycle, which was the genuinely awkward part of calling the API by hand.

**Delete the FLIP implementation before writing it.** Less code, better behaviour, and the compositor handles frames a JS loop would drop.

### The one real problem: names

`view-transition-name` must be **unique in the document at transition time**. With 12 scenes × up to 8 blocks, naive naming both collides and tanks performance — the browser snapshots dozens of elements it will never show.

Two rules:

- **Derive the name from the block id** — `vt-${block.id}`. Block ids are unique within an experience, which is already asserted by the schema
- **Only assign names to blocks currently in the viewport.** An off-screen scene has no visual continuity to preserve

`use-viewport-blocks.ts` is an IntersectionObserver returning the on-screen set. It lives in the reskin feature, not in the renderer — the renderer core may not read the environment, and this is exactly the kind of thing rule 6 exists to keep out of it.

### Two things that will not interpolate, and should not

**Text reflow cross-fades rather than animating glyphs.** That is visually correct and the reason not to fight it: where a headline reflows from two lines to three under a tighter budget, a cross-fade is what you want.

**Background and texture may take their own longer curve** via a separate `::view-transition-group` rule, so the atmospheric layer resolves after the content settles. This is the one piece of deliberate art direction in the transition itself.

### Reduced motion is a branch, and it has to be

**View Transitions do not respect `prefers-reduced-motion` on their own.** The media query is checked in the wrapper and the state is set directly, with no transition at all. Not a shorter transition — none.

This is the single most likely thing in the phase to be forgotten, because the transition works fine without the branch and the omission is invisible to everyone who does not need it.

### Unsupported browsers

`document.startViewTransition` is absent, the state updates, the page repaints. **No polyfill and no code path of your own.** That is an acceptable fallback for a visual flourish and it is why this ships without a compatibility matrix.

---

## Verify

**The gate** — green.

**Names**

- [ ] Reskin a 12-scene experience and assert **no duplicate `view-transition-name`** in the document at transition time
- [ ] Off-screen blocks carry **no** name. Assert the count of named elements is bounded by what fits a viewport, not by the size of the experience
- [ ] Scrolling changes which blocks are named, and a reskin mid-scroll still has no duplicates

**Behaviour**

- [ ] The transition runs on a reskin and the end state matches a reskin performed without one, byte for byte in the DOM. A transition that leaves different markup behind is a second render path
- [ ] `prefers-reduced-motion: reduce` produces **no transition** and a correct end state. e2e, with `emulateMedia`
- [ ] With `startViewTransition` stubbed out as undefined, the reskin still completes correctly

**Performance**

- [ ] A 12-scene reskin does not drop the frame budget on a mid-range profile. Measure it; "feels smooth" is what naming every block also felt like before it was measured

**Human**

- [ ] Reskin between all three art directions, both directions, several times. This is the screenshot people share and from v3 it is the marketing hero's one interactive control — it is allowed to take an afternoon

---

## Skipped

| Not built | Trigger |
|---|---|
| A FLIP implementation | Never. The platform does it |
| A polyfill for unsupported browsers | Never. Instant swap is the correct degradation for a flourish |
| Cross-document transitions | Not applicable. Reskin is same-document by construction |
| Per-block transition choreography | If the default cross-fade proves flat. Start with the browser's behaviour and earn every deviation from it |
| A transition on motion swap | [11](11-range.md), and probably not at all. Swapping motion changes no layout, so there is nothing to animate between |

---

## Exit gate

- [ ] Reskin animates via `<ViewTransition>` with no hand-rolled measurement anywhere
- [ ] No duplicate `view-transition-name` on a 12-scene experience, and off-screen blocks carry none
- [ ] Reduced motion skips the transition entirely and lands correctly
- [ ] An unsupported browser degrades to an instant swap with no code path of ours
- [ ] The end state is identical with and without the transition
- [ ] The gate is green
