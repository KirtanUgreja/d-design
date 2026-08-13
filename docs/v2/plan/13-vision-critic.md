# Phase 13 — vision-critic

> This phase makes true that presentational defects are caught automatically between human reviews — bounded to one revision, never an unbounded loop.

**Depends on:** 11, 12 · **Blocks:** 15 · **Spec step:** Locked decisions → vision critic

## Search

**Read first** — docs/findings.md → Process (automated gates cannot see design), docs/techstack/pipeline-tools.md (the visual verification loop), docs/techstack/ai-stack.md (vision is not scarce)

**Grep for** — the renderer, the export output, the review loop from v1 phase 07

**Verify externally** — current vision-model quality for reading type, density, spatial rhythm from a rendered slide; OpenRouter vision routes

## Make

The vision critic: after a deck is rendered, a screenshot of each slide is shown to a vision model that checks for presentational defects — overflow, cramped spacing, unreadable contrast, an empty region, a chart that renders as a grey rectangle. It applies **at most one revision** to a slide, then stops.

### Design decisions

- **The critic is bounded — one revision, then it stops.** A `for` loop with a literal limit, written in the seam. This is the documented rule from ai-stack.md: a bounded loop is not autonomy, and the moment it becomes a `while` with the model deciding how many times it runs, it is an agent and the no-framework rule is broken.
- **The critic checks structure it can see, not taste.** It flags overflow, contrast, empty regions, chart breakage — the defects findings.md measured as the real ones. It does not score beauty. Beauty stays human (v1 phase 07) — and the critic's false-positive rate is watched, because a critic that cries wolf gets ignored.
- **Vision is not scarce.** ~67 models have it, 28 open-weight. The critic is not gated on one vendor; the OpenRouter seam picks per-eval.
- **The critic is a rate, not a gate.** It does not block a merge; it flags and suggests. Structural variety (the fingerprint) gates; beauty trends, it does not block.

## Verify

- [ ] A slide with overflow/contrast/empty-region defects is flagged
- [ ] The critic applies at most one revision and stops
- [ ] False-positive rate is measured and below threshold
- [ ] **Human:** review the critic's flags on a sample deck; the ones it catches are real, the ones it misses are rare

## Skipped

- An unbounded critic loop — deliberately never. It is an agent

## Exit gate

- [ ] Critic flags real presentational defects
- [ ] Bounded to one revision
- [ ] False-positive rate measured and acceptable
