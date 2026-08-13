# Phase 15 — variety-gate

> This phase makes true that the variety claim is a standing, CI-gated metric — the v1 acceptance measurement becomes a gate every deck passes.

**Depends on:** 13, 14 · **Blocks:** — · **Spec step:** Locked decisions → fingerprint gate

## Search

**Read first** — docs/v1/plan/08-acceptance.md (the v1 fingerprint), docs/findings.md → Measured in this codebase (the 53% identical measurement), docs/techstack/ai-stack.md → Evals (structural assertions gate; probabilistic scores never gate a merge)

**Grep for** — the fingerprint code from v1, the eval harness, the `Deck` schema

**Verify externally** — current Promptfoo; how the fingerprint gate runs in CI alongside the structural assertions

## Make

The fingerprint gate: every deck render produces a design-space fingerprint (design family, layout structure per slide, chart-type distribution), and CI asserts:

- Two decks sampled from the registry differ beyond a threshold
- Within a deck, layout structures and chart types are distributed
- No presentational value passes the backstop

### Design decisions

- **Fingerprints are structural, so they gate.** This is the ai-stack evals rule: structural assertions are hard pass/fail in CI; probabilistic scores (beauty) never gate a merge. Variety is structural — the fingerprint is deterministic, so it gates.
- **The fingerprint is the "53% identical" measurement, made into a standing gate.** The old findings.md measured that three deliberately distant art directions were 53% identical. The gate exists so that number never silently creeps back.
- **The gate is per-deck and cross-deck.** Within a deck, layout structures are distributed (no repeated frame). Across decks, fingerprints differ (two decks are not the same design).
- **The gate runs in CI on the golden briefs, and it is the falsifier for the v2 bet.** If the design engine collapses — two decks converge, or a deck collapses to one frame — the gate fails and the phase fails loudly.

## Verify

- [ ] Every deck render produces a fingerprint
- [ ] Cross-deck fingerprints differ beyond threshold
- [ ] Within-deck layout/chart distribution holds
- [ ] The gate runs in CI on the golden briefs
- [ ] **Human:** a deck that passes the gate reads as varied; a deck that fails it reads as collapsed

## Skipped

- An automated beauty score in the gate — deliberately never. Beauty trends (nightly, non-blocking), structure gates

## Exit gate

- [ ] Fingerprint gate in CI
- [ ] Golden briefs pass schema-validity and variety
- [ ] The gate fails loudly if the design engine collapses
