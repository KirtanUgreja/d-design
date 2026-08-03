# Transformations

One scene tree, many presentations. Change the art direction, change the motion, change the playback mode — the content never moves.

Three axes, all independent, any combination valid:

```
art direction  ×  motion vocabulary  ×  playback mode
   3 (v2)              4                  2            = 24 presentations
```

This is what v1's architecture was for. It is also the only part of the product a user can *feel* the architecture through — everything else is invisible plumbing.

---

## Reskin

The headline feature. Same experience, different art direction, one click.

### Mechanics

```
1. snapshot current state              → history, trigger: 'reskin'
2. swap { artDirection, version }
3. re-validate every block against the target AD's budgets
4. produce OverflowReport
5. animate the transition
6. surface overflow, if any
```

Steps 1 and 3 are what make this safe. Step 5 is what makes it loved.

### The overflow problem

A 58-character headline is elegant in `editorial-light` and catastrophic in `bold-brutalist`, where the budget is 34.

```ts
OverflowReport {
  entries: { sceneId, blockId, field, current: number, budget: number }[]
}
```

**Nothing is rewritten automatically.** The reskin completes, overflowing blocks render with a visible flag, and the user gets a banner:

> *3 blocks are too long for Bold Brutalist.* → `Review` · `Shorten all with AI`

Each offers a one-click AI shorten, showing the proposed text before applying.

Auto-rewriting would be seamless and would silently alter marketing copy someone got legal approval on. For this wedge that is not a bug, it is a lawsuit. The overflow flag is deliberately visible and deliberately annoying.

### The transition — where the delight budget goes

This is the screenshot people share. **The platform now does the hard part.**

An earlier draft of this design specified a hand-rolled FLIP loop — measure every rect, swap tokens, force layout, measure again, apply inverse transforms, release. That is no longer the right answer. **Same-document View Transitions reached Baseline Newly Available in October 2025** (Chrome 111+, Edge 111+, Firefox 133+, Safari 18+), and React 19.2 ships a `<ViewTransition>` component that Next.js 16 supports natively.

A reskin is a same-document DOM state change. That is precisely what the API is for: the browser snapshots the old state, snapshots the new one, and animates between them — including the layout shift that FLIP existed to compute.

```tsx
// The whole mechanism
startTransition(() => setArtDirection(next))
```

React's `<ViewTransition>` handles the orchestration, which is the part that was genuinely awkward when calling `document.startViewTransition()` by hand — coordinating the browser's snapshot with React's render cycle.

**Delete the FLIP implementation.** Less code, better behavior, and the browser's compositor handles frames we would have dropped.

Three real constraints remain:

**`view-transition-name` collisions are the known failure mode.** Every named element must be unique in the document at transition time. With 12 scenes × up to 8 blocks, naive naming breaks immediately. Derive names from block id (`vt-${block.id}`), and **only assign names to blocks currently in the viewport** — an off-screen scene has no visual continuity to preserve, and naming everything makes the browser snapshot dozens of elements it will never show.

**Text reflow still does not interpolate.** The browser cross-fades the snapshots rather than animating glyphs, which is visually correct and the reason not to fight it. Where a headline reflows from two lines to three, a cross-fade is what you want anyway.

**Unsupported browsers degrade to an instant swap** with no polyfill and no code path of your own — `document.startViewTransition` is simply absent, the state updates, the page repaints. That is an acceptable fallback for a visual flourish, and it is why this is safe to ship without a compatibility matrix.

Background and texture can still take their own longer curve via a separate `::view-transition-group` rule, so the atmospheric layer resolves after the content settles.

`prefers-reduced-motion: reduce` → skip the transition and set state directly. View Transitions do **not** respect the media query on their own; you have to branch.

### Guarantee

Any AD applies to any experience, always. That holds only because **art directions are tokens-only** — no AD-specific layouts, no AD-specific components. The instant an AD can add a layout, reskin becomes "works unless the target AD lacks the source's layout," and the feature dies as a promise.

This is why `AD scope: tokens only` is locked in [spec.md](spec.md). It is not a simplification. It is the feature.

---

## Compare view

The same experience rendered under 3 art directions, side by side, scroll-synced.

Users decide with their eyes, not by reading AD names. Renders the hero scene of each at full fidelity; scrolling one scrolls all. Click one to apply — which runs the reskin flow, transition and all.

*Bet, not commitment:* users may decide from thumbnails and never open this. Cheap enough to try, first thing to cut.

---

## Motion swap

Same mechanics, far simpler. Motion vocabulary is a separate reference on the experience; swapping it changes no layout, produces no overflow, needs no snapshot beyond ordinary history.

Each AD names a `defaultMotion`, so the pairing stays curated. The other eleven combinations are available and unrecommended — `bold-brutalist` + `cinematic-slow` is a real aesthetic choice, just not one to put on the default path.

---

## Slides mode

Deferred from v1. Same tree, different playback.

**One scene = one slide.** No content changes, no second authoring pass, no auto-splitting into narratively stupid places.

What changes:

| | Scroll | Slides |
|---|---|---|
| Motion trigger | 25% in viewport | on advance |
| Durations | full | ~30% shorter — a slide advance is a beat, not a journey |
| Parallax | on | off entirely |
| Scene padding | `clamp(6rem, 14vh, 12rem)` | collapsed to fit viewport |
| Navigation | scroll | arrow keys, clicker, click (from v1) |

Each `MotionVocabulary` carries a `slidesVariant` holding the retimed values. Slides mode is a lookup, not a code path.

### Overflow, again

Content that fits a tall scroll scene may not fit a fixed viewport. **Reuse `OverflowReport`** — same type, same banner, same shorten-with-AI affordance, computed against viewport height instead of character budget.

Two features, one mechanism. If slides mode needs its own overflow concept, one of the two designs is wrong.

### ScrollSequence in slides mode

A scroll-driven image sequence has no scroll to drive it. It degrades to a single representative frame, and the editor says so when the user switches modes. See [primitives.md](primitives.md).

---

## Version history

Not a feature. The safety net that makes every transformation above acceptable to ship.

```
snapshots  id, experience_id, scenes (jsonb), art_direction,
           motion_vocabulary, mode, label, trigger, created_at
```

**Auto-snapshot before every destructive action:** reskin, scene regenerate, bulk edit, mode switch, publish. Plus user-named checkpoints, unlimited.

Retain the last 50 auto-snapshots; named ones forever. A scene tree is a few KB of JSON — storing 50 whole copies costs less than reconstructing state from a patch log, and answers the only question users actually ask: *put it back the way it was before I clicked that.*

Restore writes the snapshot back as current state, after snapshotting the present. Restoring is itself undoable.

Full undo/redo at keystroke granularity is deliberately not built. It is editor-grade work for a need that milestone snapshots already cover.
