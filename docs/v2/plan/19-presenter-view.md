# Phase 19 — Presenter view and speaker notes

> The audience sees the slide. The presenter sees the notes, the timer and what is coming next. `Scene.notes` has existed since v1 and has never been written to — this is the phase that fills it and then shows it to the only person who needs it.

**Depends on:** [10](10-slides-mode.md), [18](18-presentation-frame.md) · **Blocks:** [23](23-phone-remote.md) · **Spec step:** presentation delta

---

## Search

**Read first**

- [../presentation.md](../presentation.md) → "The live room"
- [../../v1/spec.md](../../v1/spec.md) → Risk 2, AI-invented marketing claims. **This phase is where that risk gets worse**, because a presenter reads notes aloud in a real meeting without re-reading them first
- [../../v1/ai-pipeline.md](../../v1/ai-pipeline.md) → the Build phase. Notes are drafted there, not in a fifth call
- [../../v1/scene-schema.md](../../v1/scene-schema.md) → `notes?: string`, declared in v1 and unused

**Grep for**

- `api/schema/scene.py` → `notes`. It exists, it is optional, and it has no budget. Both of the last two change
- `web/src/features/present/fullscreen.tsx` → the playback wrapper. Presenter view is a second window driven by the same advance logic, **not a second renderer**
- `api/features/art_direction/__init__.py` → `budgets`. Notes get one, per art direction like everything else
- `web/src/features/editor/` → wherever a block's props are edited. Notes are edited per slide and the affordance belongs with the existing property panel rather than in a new surface

**Verify externally**

- `BroadcastChannel` support and behaviour across two windows of the same origin, including whether it survives one window being on a second display
- The Window Management API (`getScreenDetails`) — permission prompt wording, Chromium-only status, and what it does in Firefox and Safari. **The base mechanism must not depend on it**
- Whether `requestFullscreen` on the presentation window is affected by the presenter window taking focus. This is the one that breaks on stage

---

## Make

```
web/src/features/present/
  presenter.tsx          the second window: notes, timer, next slide
  channel.ts             advance sync between the two windows
  timer.tsx              elapsed, and a target from the deck's length
api/features/build/      notes drafted in the Build phase
```

### The AI drafts the notes

The Build phase already knows the Brief, the slide's `intent` and its blocks. Drafting *what to say out loud* is one more field in an existing call — **not a fifth pipeline phase**, and not a separate button the user has to find.

Three constraints, all of which exist because a presenter will say this in a room:

1. **Grounded in the Brief, never embellished.** The same rule the Build prompt already carries for on-slide copy. A note that invents a customer name or a number is worse than an on-slide one, because nobody proofreads what they are about to improvise from
2. **Budgeted, per art direction, like every other text field.** A note nobody can scan in the two seconds before advancing is not a note. The budget is measured in what fits presenter view without scrolling
3. **Reviewable at the outline gate**, alongside everything else the AI asserts

Notes say *how to deliver the slide* — where to pause, what to open with, what not to read aloud. They are not a transcript of the slide, and a note that restates the headline is a defect the eval corpus should catch.

### The presenter window

A second window at the same origin, opened by the presenter, synced over `BroadcastChannel`. Whichever window has focus can advance; both stay on the same slide.

**The base mechanism works in every browser.** The Window Management API is progressive enhancement on top: with permission, the presenter window is placed on the internal display and the deck goes fullscreen on the external one automatically. Without it, the user drags one window across, which is what they already do with PowerPoint. Chromium-only capability must never be the difference between working and not working — it is the difference between two seconds and twenty.

Contents, in priority order: **the notes**, the timer, the next slide, the slide number. The next-slide preview is the renderer at a small stage size, which works without a single change because of [18](18-presentation-frame.md)'s container units — a preview is just a smaller container, and its type scales to it.

### The timer

Elapsed time, and a target taken from the talk length captured in [22](22-deck-length.md). Pace against target is the useful signal, not raw elapsed — *"slide 4 of 12, six minutes in, of fifteen"* tells a presenter something; a stopwatch does not.

---

## Verify

**The gate** — green.

**Notes**

- [ ] Every generated slide has notes, and they pass the no-styling invariant test like every other AI-authored string
- [ ] A note that exceeds its budget is flagged through the existing mechanism, not a new one
- [ ] The eval corpus gains a check that notes do not merely restate the slide's headline
- [ ] Notes are editable per slide in the existing property panel, with no new surface
- [ ] Notes never appear in the published deck, the handout view, the PDF, or the embed. **Greppable, and tested** — a note leaking into an audience-facing surface is the failure that matters here

**Presenter view**

- [ ] Two windows stay in sync in both directions, in a browser without the Window Management API
- [ ] With the API and permission granted, the windows land on the correct displays unprompted
- [ ] With the API and permission **denied**, everything still works. Rule 10 — anything that grants, fails closed, and the closed state here is "manual, not broken"
- [ ] Advancing from a clicker while the presenter window has focus advances the audience window
- [ ] The next-slide preview renders through the same renderer with no new props

**Human**

- [ ] Present a real deck to a real person, from a laptop connected to an external display, using a real clicker. Every defect in this phase is a stage defect and none of them will show up in a test

---

## Skipped

| Not built | Trigger |
|---|---|
| Notes as a full script | Never. A script gets read aloud, and a presenter reading is worse than a presenter talking |
| Rehearsal mode with per-slide timings | If presenting reveals the need. The timer is the cheap 80% |
| Auto-advance / kiosk playback | Belongs with the shared link, not the live room. v3 if analytics show link-viewers stalling |
| Audience-visible timer or progress bar | An art direction decision, not a playback one. Route it through tokens if it ever lands |
| Notes in a second language | [../../v3/localization.md](../../v3/localization.md) — transcreation covers the tree, and notes are part of the tree |

---

## Exit gate

- [ ] The Build phase drafts grounded, budgeted notes for every slide
- [ ] Notes are reviewable at the outline gate and editable per slide
- [ ] Notes cannot reach any audience-facing surface, and there is a test that proves it
- [ ] Presenter view syncs in every browser; screen placement is enhancement only and fails closed
- [ ] The next-slide preview reuses the renderer with no new props
- [ ] A real deck presented to a real person, on real hardware
- [ ] The gate is green
