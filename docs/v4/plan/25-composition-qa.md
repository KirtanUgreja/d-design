# Phase 25 — composition and QA

> This phase makes true that the engine is reliable, not just capable: varied slides with real charts and images, at target cost, with no visible defect reaching a user. **It ends at the second human gate.**

**Depends on:** 23, 24 · **Blocks:** 26, 27 · **Spec step:** Commitments → components, measured in Chromium; Risks 1, 2, 7 · **Size:** L

## Search

**Read first** — [../design-engine.md](../design-engine.md) → Compositions, Exemplars, "QA metrics", "Repair ladder", Components; [../bench.md](../bench.md) → Budgets

**Grep for**
- The phase-22 exemplar A/B result in `bench/results.md` — it decides whether the library grows.
- Every defect the owner tallied on earlier walls that no metric flagged.

**Verify externally**
- The image models available through OpenRouter, their sizes and prices.
- AeSlides' whitespace and balance definitions (arXiv 2604.22840), for W1–W3.

## Make

- `compose/planner.py`: 15 intents, 10 archetypes, the rhythm rules.
- The exemplar library to about 40, drafted by the design model and curated by the owner — **only if the A/B showed exemplars help**.
- `dd-chart`: bar, column, line, donut, with golden files.
- `dd-image`: 0–4 per deck with a "why", treatments, webp, the XMP tag, the text check with one regeneration.
- `dd-texture`.
- The full metric set, including pixel contrast and the computed-style check.
- The repair ladder: ≤2 rounds → exemplar-fill → flag.
- Five slides in parallel; the per-deck `budget_usd` cap.
- The image-model bake-off.

### Design decisions

- **Charts only from approved facts.** No fact, no chart; the planner picks another intent.
- **A failed image never fails a deck.**
- **Warnings stay warnings** until the bench shows they track the owner's scores.

**Built without model credit (2026-10-05):** charts from approved facts; the planner's 10 archetypes and rhythm rules; the repair ladder (2 rounds → exemplar-fill → code layout → flag); the seam's budget guard; E5 on pixels and warnings W1–W6 (`qa/pixels.js`, `qa/metrics.py`). **Still to build, needing credit:** `dd-image` and the image-model bake-off; then the 12 × 2 end-to-end run and gate 2. The exemplar library stays at 12 until the owner curates drafts.

## Verify

- [x] Chart golden files (`tests/golden/charts/`, 2026-10-05)
- [ ] 12 briefs × 2 seeds, end to end from the content engine's outlines
- [x] A budget check that throws refuses the call (`tests/test_seam.py`)
- [ ] **Human (gate 2):** "would send this to an investor or a customer", blind, against the baselines

## Skipped

- Icons — trigger: the wall shows process slides failing without them.
- Tables — trigger: pricing slides fail on the wall.

## Exit gate

- [ ] Gate 2: yes for at least 9 of 12 decks
- [ ] At least 95% of slides defect-free; ≤10% exemplar-filled; ≤3% flagged
- [ ] Median ≤ $2; p90 ≤ 5 minutes
- [ ] Median export ≤ 6 MB
- [ ] No two consecutive slides share a fingerprint in any deck
