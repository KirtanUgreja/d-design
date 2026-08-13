# Phase 08 — acceptance

> This phase makes true the claim that the product works: a golden run of real briefs produces schema-valid, varied, offline decks — measured, not vibes.

**Depends on:** 07 · **Blocks:** — · **Spec step:** Commitments vs bets, Risks

## Search

**Read first** — docs/findings.md → Measured in this codebase (the 53% identical measurement), docs/findings.md → Model behaviour (mode collapse), docs/techstack/ai-stack.md → Evals

**Grep for** — the `Deck` schema, the design registry, the export output, any existing eval harness

**Verify externally** — current Promptfoo version; how to run the golden briefs through the pipeline headlessly

## Make

The acceptance run: a golden set of briefs (5–10 real ones) run through the whole pipeline — interview → mapping → build → review → export — with two assertions: **schema-validity** and **variety**.

### Design decisions

- **A golden briefs set, checked into the repo.** This is the eval dataset. 5–10 real briefs (product launch, fundraising, sales, internal, conference talk) that exercise different topics and lengths.
- **Images are part of the golden run.** The briefs exercise decks that want images (a product launch wants a hero; a data deck wants chart companions). The acceptance run asserts generated images are embedded (data URIs, no external request), dimension-capped, and schema-valid as image blocks. Image *quality* is a human review (phase 07) and an eval trend, not a structural gate.
- **The variety metric is a fingerprint, not a vibe.** Every deck render produces a design-space fingerprint — which design family, which layout archetypes per slide, the distribution. The acceptance run asserts:
  - Two decks sampled from the registry differ in fingerprint beyond a threshold
  - Within a deck, layout archetypes are distributed (a 12-slide deck does not use one archetype 8 times)
  - No presentational value passes the backstop
- **This is the falsifier for the core bet.** If two decks converge on the same fingerprint, or a deck collapses to one repeated frame, the design system is not doing its job and the phase fails. This is the "53% identical" measurement from findings.md, made into a gate.
- **The gate stays green.** The acceptance run is part of CI. A probabilistic *beauty* score is deliberately absent — only deterministic structural variety is gated. Human review (phase 07) handles the beauty.

## Verify

- [ ] 5–10 golden briefs run end-to-end
- [ ] 100% schema-valid output
- [ ] Fingerprints differ across decks beyond threshold
- [ ] Layout archetypes distributed within each deck
- [ ] No presentational values pass the backstop
- [ ] Generated images are embedded, dimension-capped, and schema-valid
- [ ] **Human:** the golden decks look like decks a presenter would actually give

## Skipped

- An automated beauty score / vision critic — v2
- Quality-scoring eval layer — v2

## Exit gate

- [ ] Golden briefs pass schema-validity and variety assertions
- [ ] Fingerprint metric is checked into CI
- [ ] A human has reviewed the golden decks
