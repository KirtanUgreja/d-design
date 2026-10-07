# Phase 34 — presenter confidence

> This phase makes true that the end of the experience is a calm presentation, not a nervous one: the user can rehearse their own deck with their notes and timing, and walks on stage knowing what comes next.

**Depends on:** 26, 28 · **Blocks:** 35 · **Spec step:** Locked decisions → Presenting · **Size:** S/M

## Search

**Read first** — [../ui-research.md](../ui-research.md) → rehearsal and anxiety, peak-end; [26-player-export.md](26-player-export.md); [../content.md](../content.md) → notes

**Grep for**
- `api/engine/export/player.js` — the presenter popup this phase extends.
- `Brief.minutes` and `Brief.delivery` — the time the user said they have.

**Verify externally**
- What rehearsal features exist in PowerPoint and Keynote today, so ours is not a weaker copy.

## Make

- **Rehearse mode, in the present export:** the real deck and the presenter view, with a per-slide timer against the minutes the user gave, a pace marker ("on time", "1 min over"), and notes as prompts in large type.
- **A rehearsal summary** after each run-through: total time, the slides that ran long, and slides with no notes. Stored in the browser only; nothing leaves the file.
- **A ready check before presenting:** no flagged slides, notes on every slide, total time fits. Each item links back to the slide.
- **Clicker and second-screen tested**, building on phase 26's popup.

### Design decisions

- **No AI judging their voice or face.** Rehearsal is practice with the real material and honest timing; a judging assistant raises the anxiety it claims to lower.
- **Offline, like the file.** Rehearsal runs inside the exported `.html`, with zero network requests.

## Verify

- [ ] Rehearse mode adds no network request (the offline test)
- [ ] The timer and summary are correct against a scripted run
- [ ] **Human:** 3 users rehearse a deck twice, then present it; ask how ready they felt before and after

## Skipped

- Speech analysis, filler-word counting — never in the file; reconsider only on repeated user demand.
- A phone remote — trigger in [26-player-export.md](26-player-export.md).

## Exit gate

- [ ] At least 2 of 3 users report feeling more ready after rehearsing
- [ ] Zero stage defects in the human run

## Sprint status (2026-10-08) → [master-plan.md](master-plan.md)

The player's presenter view (notes, timer, next slide) is built (phase 26). **Rehearse mode, the summary and the ready check move after submission.** Trigger: the first user who presents a generated deck.
