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

This is the screenshot people share. It is also genuinely hard, because text reflow does not interpolate.

**Approach: FLIP across the token swap.**

```
1. measure every visible block's rect          (First)
2. swap tokens; force layout                   (Last)
3. measure again; apply inverse transforms     (Invert)
4. release, animating to identity              (Play)
5. cross-fade type: old text ghost fades out over new, 240ms
6. background and texture cross-fade on their own curve, 600ms
```

Total ~800ms. Blocks slide and scale to their new positions while type cross-fades in place — the layout appears to *rearrange itself* rather than being replaced.

Only visible blocks are animated. Off-screen scenes swap instantly, since nobody is watching them and animating 12 scenes at once will drop frames.

**Ship it as a 200ms cross-fade first.** Get the whole matrix correct and boring, then spend real time making one transition beautiful. Do not let the animation block the feature.

`prefers-reduced-motion: reduce` → instant swap, no transition.

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
