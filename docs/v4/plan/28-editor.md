# Phase 28 — editor

> This phase makes true that a deck can be fixed and tuned without breaking it: text edits, AI edits per slide, look changes, and undo, all re-checked by QA.

**Depends on:** 27 · **Blocks:** 29 · **Spec step:** Risk 5 · **Size:** L

## Search

**Read first** — [../../design/app.md](../../design/app.md) → The editor, "The colour picker that does not exist"; [../design-engine.md](../design-engine.md) → "Sampler and theme" (the two tiers)

**Grep for**
- `revise_slide` in `api/pipeline/review/review.py` at `v3-final` — the idea to port into `compose/revise.py`.
- The v3 `editor.store.ts` undo — it snapshotted per keystroke; do not repeat it.

**Verify externally**
- Do a parent's listeners and `contenteditable="plaintext-only"` work inside a same-origin iframe without `allow-scripts`, and inside an open shadow root, in Chrome, Safari and Firefox?
- Fallback if not: `allow-scripts` plus a hashed edit bridge over `postMessage`.

## Make

- **Filmstrip** of QA screenshots: reorder, add (pick an intent), duplicate, delete.
- **Canvas:** a `srcdoc` iframe, `sandbox="allow-same-origin"`, scaled to fit. Click a field to edit; each save is an edit job that re-renders and re-runs QA. Overflow offers "Fit to slide".
- **Slide panel:** a free-text instruction and quick actions — Regenerate · Different layout · Shorter · Add image · Turn into chart · Split — each with a before/after compare to accept or discard.
- **Notes** editing.
- **Look:** recolour and pairing swap (deterministic + QA); restyle (regenerate with the content locked, cost shown first).
- **Undo/redo** as labelled snapshots per operation; autosave.
- Export dialog; Present.

### Design decisions

- **No HTML or CSS authoring by the user, and no free colour picker.** The look is the unit of style.
- **Every edit goes through QA.** An edit that breaks a slide is offered a fix, never silently saved broken.

## Verify

- [ ] Edit round-trip tests: a field edit changes the plan and the HTML together
- [ ] At least 16 of 20 live instructions accepted on the first candidate
- [ ] After a recolour, under 30% of slides need repair
- [ ] **Human:** the owner edits 3 decks for 10 minutes each and lists every friction

## Skipped

- Drag-to-move elements — trigger: the human check shows the need.
- Image upload — trigger: phase 29.

## Exit gate

- [ ] Every friction from the human check is fixed or recorded as Skipped with a trigger
- [ ] Undo restores any of the last 20 operations exactly

## Sprint status (2026-10-08) → [master-plan.md](master-plan.md)

Built 2026-10-07: text edits, reorder, delete, recolour, Fit to slide, labelled undo/redo (20 steps), the live editor screen.

**Build day (2026-10-09, B11, P1):**
- **AI edit by instruction:** the instruction goes to a revise job; the candidate is rendered and shown **beside** the current slide; accept makes it a labelled version, discard drops it. Instructions about colour or type get the designed refusal (no model call) and point to *Another style* or *New colours*.
- **Notes editing** (an edit operation, no QA needed) and **duplicate slide**.
- "Add slide" stays after submission (it needs a compose call and a content step).

**Test day:** 5 live instructions on one deck (about $0.10); the owner's friction check moves after submission.
