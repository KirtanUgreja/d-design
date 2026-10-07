# Phase 32 — the watch and the reveal

> This phase makes true that the two moments people remember — the peak and the end — are the best-crafted in the product: the cover arriving first, slides filling known slots with real work visible, and a reveal they want to show someone.

**Depends on:** 30, 27 · **Blocks:** 35 · **Spec step:** Commitments → the watch · **Size:** M

## Search

**Read first** — [../ui-research.md](../ui-research.md) → labor illusion, peak-end, Doherty threshold, skeletons; [../../design/app.md](../../design/app.md) → §4 the watch, §6 present and export; [../engine.md](../engine.md) → "Generation jobs and events"

**Grep for**
- The event names the pipeline emits, and their order, in a recorded bench run.
- `bench/ui/baseline.md` — "felt stuck", aborts, and what participants said at the reveal.

**Verify externally**
- `prefers-reduced-motion` behaviour in Chromium, Firefox and WebKit for the motion this phase adds.

## Make

- **Ghost slots from the approved outline**, each labelled with its headline, so the end is in sight from the first second (goal-gradient).
- **The cover first, at size.** The pipeline composes slide 1 before the rest and the watch shows it the moment it is measured: the product's peak.
- **Real work, visible.** Each slot moves through real states only — *writing*, *composing*, *checking*, *done* — from the event log. No invented steps, no added delay (the ethics line).
- **Arrival motion** that respects the theme's motion axis and reduced motion: a slide settles into its slot; nothing bounces.
- **Silent repairs, honest flags.** A repaired slide just arrives; one that needed exemplar-fill or a flag says so in plain words with one action.
- **The reveal:** the whole deck as a contact sheet in its look, the cover large, three actions in human words — *Present (your notes are inside)*, *Download to send (slides only)*, *PDF*. Flagged slides named before any download.
- **Abort and continue** keep every finished slide.

### Design decisions

- **The labor illusion is earned, not staged.** Operational transparency raises perceived value only because the work is real; adding delay to look busy is banned.
- **Peak and end get the craft budget.** A failure is never the last thing the user sees: it is followed by what still works and one next step.

## Verify

- [ ] The first slide appears within 60 s of approval (median), and it is the cover
- [ ] Every state shown in the watch maps to a real event; a test replays a log and checks the mapping
- [ ] Reduced motion: no animation, same information
- [ ] **Human:** 5 users watch a real generation; ask afterwards what was happening and how they felt at the reveal

## Skipped

- Sound — never.
- Confetti or celebration effects — never; the deck is the celebration.

## Exit gate

- [ ] No participant reports the watch as "stuck" or "fake"
- [ ] At least 3 of 5 want to show the deck to someone (asked, not prompted)
- [ ] Beats phase 30's baseline on the post-session rating

## Sprint status (2026-10-08) → [master-plan.md](master-plan.md)

Done: the cover composed first and shown first (2026-10-07); ghost slots from the outline; arrival motion; abort and continue keeping finished slides; the reveal with Present / Download / PDF.

**Build day (B13, P1):** real states per slot from the event log (*composing*, *checking*, *done*, *needs attention*) and flagged slides named before any download. **After submission:** the 5-user session.
