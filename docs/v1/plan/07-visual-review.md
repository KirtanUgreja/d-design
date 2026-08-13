# Phase 07 — visual review

> This phase makes true that a human actually looks at the generated deck before it ships — because the automated gate verifies structure, and every real defect is presentational.

**Depends on:** 05 · **Blocks:** 08 · **Spec step:** The flow, Risks

## Search

**Read first** — docs/findings.md → Process ("The quality apparatus verified structure, and every real defect was presentational"), docs/design/principles.md, docs/coderules/ai-authorship.md

**Grep for** — the export output, the acceptance run from phase 08

**Verify externally** — how to present the exported HTML for human review (a review screen, a file, a screenshot)

## Make

The visual review loop: after the deck is exported, a human reviews it — slide by slide, in the browser, at full size — and can send specific slides back for regeneration with written feedback.

### Design decisions

- **The review is human, not an AI judge.** v1 does not use a vision-model critic to score beauty. The findings.md evidence is blunt: automated gates cannot see design, and the previous release's every real defect was presentational. A human looks.
- **Image quality is reviewed like any other block.** Generated images are new works — wrong subject, off-family palette, or a grey rectangle from a transient failure are visible defects a reviewer catches here. A slide with a bad image is sent back for regeneration with written feedback, same as any other slide (`docs/v1/spec.md` → Risk 6).
- **The review is a loop, not a gate.** A slide can be sent back for regeneration with feedback. The repair is a per-slide re-call, cheap and bounded.
- **The review is where "does this read as authored" is decided.** The reviewer checks layout distribution, cohesion, no repeated frame, and whether the deck reads as one designed thing. This is the human half of the variety bet.
- **The review precedes the acceptance run.** It is the last human step before the variety measurement.

## Verify

- [ ] A reviewer can open the exported deck, view each slide, and send slides back
- [ ] A slide sent back regenerates and re-exports
- [ ] **Human:** review a sample deck; confirm it reads as authored, not assembled; layouts distributed; no repeated frame

## Skipped

- A vision-model critic / automated beauty score — v2. v1 is human review

## Exit gate

- [ ] Human review loop works
- [ ] A regenerated slide re-exports correctly
