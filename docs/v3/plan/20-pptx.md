# Phase 20 — PPTX export (conditional)

> This phase makes true that a deck can be exported to native PPTX — but only if the market asks, and only as native OOXML generation, never a lossy conversion.

**Depends on:** 19 · **Blocks:** — · **Spec step:** Locked decisions → PPTX export

## Search

**Read first** — docs/findings.md → The category ("Lossy web-to-PowerPoint export is the category's worst-reviewed feature... Native OOXML generation is the only version that does not lose them"), docs/v1/plan/05-export.md (the single-file exporter)

**Grep for** — the exporter, the renderer, the `Deck` schema

**Verify externally** — the current state of native OOXML generation from a deck-shaped model; whether the market has actually asked

## Make

**Conditional phase.** Native PPTX export: generate a real `.pptx` (OOXML) from the `Deck` — text, layout, color, and static chart rendering survive. What cannot survive (web fonts, texture, motion) is explicitly handled, not silently lost.

### Design decisions

- **It is conditional.** The trigger is a real signal from the market: users asking for PowerPoint export, or a competitor's export becoming a complaint. Until then, HTML + PDF are the product and this phase does not start.
- **Native OOXML, never a screenshot-to-PPTX.** The category's worst-reviewed feature is lossy web-to-PPTX — text shifts, spacing changes, fonts substitute. A screenshot would inherit that. Native generation is the only version that does not lose fonts, texture, and motion — and the ones that cannot survive (motion) are handled explicitly: PPTX gets the resting state, the same as PDF.
- **The `Deck` schema is the source.** PPTX is a *render* of the deck, like the HTML and PDF — a third view of the same source of truth, not a second source.
- **The single-file HTML remains the product.** PPTX is an interop convenience for the audience that lives in PowerPoint. It is built last, conditional on demand.

## Verify

- [ ] Native `.pptx` generated from the `Deck`
- [ ] Text, layout, color, static charts survive; motion is the resting state
- [ ] No lossy conversion path exists
- [ ] **Human:** open the `.pptx` in PowerPoint; it reads as the deck, not a flattened image

## Skipped

- PPTX *round-tripping* (editing a deck in PowerPoint and bringing it back) — a whole second product, not built
- If the market never asks, this phase is skipped entirely and the trigger stays written down

## Trigger status (2026-08-15)

**Not started — the market trigger is not met.** The phase is conditional on a
real signal (users asking for PowerPoint export, or a competitor's export
becoming a complaint), and there is no such signal in the repo: no user
requests, no documented competitor-export complaint against us, no market
intelligence naming PPTX. The v3 spec frames it as a live question, not a
decision to build.

What exists today that would make the phase *small* if the trigger fires:
- The `Deck` schema (api/schema/deck.py) is the source of truth — PPTX is a
  third render of it (like HTML and PDF), never a second source.
- The PDF path (phase 14) already establishes "motion prints as the resting
  state" — the same rule PPTX needs.
- The find/replace surface for a native OOXML generator would slot beside the
  exporter (render/), not a new pipeline.

The trigger stays written down: **users asking for PowerPoint export, or a
competitor's export becoming a complaint.** Until then, HTML + PDF are the
product, and the phase does not start.

## Exit gate

- [ ] Market trigger met
- [ ] Native OOXML export faithful to the `Deck`
- [ ] No lossy conversion path
