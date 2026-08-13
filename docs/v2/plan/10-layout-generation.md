# Phase 10 — layout-generation

> This phase makes true the core v2 bet: the model designs new layouts within the family's grammar, rather than picking from a curated catalogue.

**Depends on:** 09 · **Blocks:** 11, 12 · **Spec step:** Locked decisions → layouts

## Search

**Read first** — docs/findings.md → Model behaviour (diversity is architecture, not prompting), docs/v1/plan/04-slide-builder.md (per-slide generation), docs/v1/plan/03-mapping.md (layout distribution)

**Grep for** — the layout archetype catalogue, the `Deck` schema's layout field, the slide-builder prompt

**Verify externally** — how to constrain a model to a layout grammar via JSON Schema; the current best model for "given content + a family grammar, produce a valid layout"

## Make

The mapping and slide-builder phases learn to generate layouts within a family's grammar: a grammar defines the *legal moves* (how many blocks, which regions, which size relationships), and the model picks the move and the values within it — rather than picking from a fixed catalogue.

### Design decisions

- **The grammar, not the catalogue, is the constraint.** The model chooses *which* layout structure and *how* it is filled, but only within the family's grammar. This is the structured-diversity finding from findings.md: sample the discrete choices structurally, let the model fill continuous values within the region it was handed.
- **The grammar is per-family.** Each family declares its own grammar — what layouts are legal in it. This is what keeps a generated layout on-family and the deck cohesive.
- **Layout generation is still per-slide.** Each slide is a separate call. The distribution guarantee (a 12-slide deck does not repeat one frame) is enforced by the mapping pass, which now tracks the *grammar space* rather than a fixed catalogue.
- **The fingerprint now includes layout structure.** The variety gate (phase 15) needs to measure that generated layouts differ, not just that the catalogue was sampled widely.

## Verify

- [ ] The model generates valid layouts within a family's grammar
- [ ] A 12-slide deck has distributed layout structures (no repeated frame)
- [ ] Generated layouts stay on-family (they read as the same design system)
- [ ] **Human:** generated layouts look as good as the v1 curated ones

## Skipped

- Grammar *evolution* (the model inventing new grammar rules) — v3. v2 is generation within a fixed grammar

## Exit gate

- [ ] Grammar-constrained layout generation works
- [ ] Distribution and on-family checks pass
- [ ] Generated layouts beat curated ones at ≥ chance in a blind test
