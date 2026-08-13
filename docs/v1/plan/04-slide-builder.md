# Phase 04 — slide-builder

> This phase makes true the core claim: each slide is generated individually, in HTML, from a per-slide spec and a per-deck design family — so the deck reads as authored, not assembled from repeated frames.

**Depends on:** 03 · **Blocks:** 06 · **Spec step:** The flow, Commitments vs bets → per-slide generation

## Search

**Read first** — docs/coderules/patterns.md (rule 1, no-styling), docs/v1/spec.md (the flow), docs/techstack/frontend.md (published artifact, progressive enhancement)

**Grep for** — the `Deck` schema, the design registry, any existing HTML generation

**Verify externally** — the OpenRouter seam; which model scores best on "given a slide spec + a design family, produce valid slide HTML with no presentational values"

## Make

The slide builder: for each slide in the mapped `Deck`, a plain deterministic orchestrator calls the model once with a per-slide prompt (the slide spec, the design family, the design rules) and gets back a valid slide definition. The slide is validated, then rendered.

### Design decisions

- **One model call per slide.** Each slide gets its own prompt and its own schema-validated result. This is the "different skills and plugins" — the per-slide prompt carries the design rules, the layout archetype, the motion vocabulary, and the chart shape.
- **Images are generated, not placed.** The slide builder decides per-slide whether an image earns its place — background, hero, illustration, chart companion — and prompts an **OpenRouter image model** within the design family's visual rules (palette, texture, composition). The image is generated, capped in dimension, and embedded as a data URI at export (`docs/v1/plan/05-export.md`). The deck's no-styling invariant holds: the model says *what* the image is, the family styles it.
- **The slide carries no presentational values.** The model emits *what* is on the slide and *which layout archetype* — the *how it looks* comes from the design family's tokens in the renderer. This is what keeps a deck cohesive (constant design system) while each slide is individually generated.
- **Per-slide generation is the variety mechanism.** Because each slide is a separate call with a distinct spec, the model cannot collapse the whole deck into one frame. The design family provides the constant; the per-slide spec provides the variation.
- **The slide builder is where the "beautiful" actually happens.** This is the craft budget. The per-slide prompt is the most-tuned prompt in the system — it is versioned, eval'd, and repaired (the model seam's single repair retry).
- **Streaming is not needed in v1.** The unit is a whole validated slide, not a token. The user watches slides assemble (perceived speed) but there is no partial-object streaming.

## Verify

- [ ] A per-slide prompt produces a schema-valid slide for each archetype in the registry
- [ ] The slide carries no presentational values (structural + backstop)
- [ ] Two slides with the same archetype but different content look distinct
- [ ] **Human:** a 12-slide deck built this way reads as authored, not assembled; layouts are distributed; no repeated frame

## Skipped

- Per-slide layout *generation* (model designing brand-new layouts) — v2
- Complex charts — v2
- Editor — v2

## Exit gate

- [ ] Every archetype in the registry produces a valid slide
- [ ] A full deck can be built slide-by-slide
- [ ] No presentational values pass the backstop
