# Phase 33 — trust and control

> This phase makes true that a user trusts what the machine wrote enough to present it to skeptics: every claim shows where it came from, every AI change is a proposal they accept, and nothing they did is ever lost.

**Depends on:** 30, 27, 28 · **Blocks:** 35 · **Spec step:** Bets → facts; Commitments → the editor · **Size:** M

## Search

**Read first** — [../ui-research.md](../ui-research.md) → control and reversibility, provenance, IKEA effect; [../../design/app.md](../../design/app.md) → §2 the outline gate, §5 the editor, "The colour picker that does not exist"; [../content.md](../content.md) → provenance and the Fact ledger

**Grep for**
- `Fact.flags`, `status="proposed"` and `provenance` in `api/engine/` — what the UI must show.
- `bench/ui/baseline.md` — every moment a participant doubted a number or feared losing work.

**Verify externally**
- How two current AI editors present before/after for a rewrite, and how they label undo.

## Make

- **Provenance you can open:** YOU / WEB / AI chips on every field; a WEB chip opens the source title, date, the exact quoted line and the link; flags ("older than 3 years", "conflicts with…") shown in words.
- **The number gate:** an unsourced number is highlighted until the user approves it as illustrative, adds a source, or cuts it. Approve is disabled while one is pending, and says why.
- **Proposals, not replacements:** every AI change — a slide instruction, a quick action, a deck-wide request, a look change — arrives as a side-by-side before/after to accept or discard.
- **Labelled undo and history:** each operation is one named version ("Made slide 4 more visual"); undo and redo are visible buttons, not only shortcuts.
- **The refusal, designed:** "make the headline red" gets a short, positive answer and the two real routes (a palette variant, more emphasis). The copy has an owner and a test.
- **Resume exactly:** an interrupted outline, generation or edit reopens where it stopped (the Ovsiankina effect holds; nothing is lost).

### Design decisions

- **The user decides, the machine labours.** Approval at the outline, the pick of a look, and accepting each change make the deck theirs (IKEA effect) without making them do the work.
- **Trust is shown, not claimed.** No "verified" badge: the source and its quote are on screen.

## Verify

- [ ] A test walks every Fact flag and every provenance chip through to its popover copy
- [ ] Approve stays disabled with a proposed number pending, in a UI test
- [ ] Every AI operation produces exactly one labelled version; undo restores byte-identical slides
- [ ] **Human:** 5 users find and check the source of a number, and recover from a bad AI edit, unaided

## Skipped

- Editing a source's quote — never; a quote is evidence.
- Collaborative comments — trigger: a team asks.

## Exit gate

- [ ] 5 of 5 users can say where a chosen number came from
- [ ] 5 of 5 recover from a bad AI edit in one action
- [ ] Undo-after-accept below 25% on live instructions (an accept that is immediately undone is a wrong proposal)

## Sprint status (2026-10-08) → [master-plan.md](master-plan.md)

Done: provenance chips with source popovers and flags; the number gate (Approve disabled while a number is unsourced); labelled undo and redo; resume after interruption (the worker). **Build day:** proposals before/after and the designed refusal arrive with 28's AI edits (B11). **After submission:** the 5-user session and the undo-after-accept measure.
