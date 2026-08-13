# Phase 03 — mapping

> This phase makes true that the approved outline becomes a precise per-slide spec — content, layout, animation, charts — that the slide builder can execute one slide at a time.

**Depends on:** 01 · **Blocks:** 04 · **Spec step:** The flow, Locked decisions → within-deck variety

## Search

**Read first** — docs/coderules/patterns.md (rule 1, no-styling), docs/v1/spec.md (the flow), docs/design/principles.md

**Grep for** — the outline shape from phase 02, the `Deck` schema from phase 01

**Verify externally** — how a layout-archetype catalogue should be structured so the model picks rather than invents

## Make

The mapping pass: a plain, deterministic orchestrator takes the approved outline and produces a **per-slide spec** — a `Deck` with each slide assigned a layout archetype, content blocks, motion intent, and (where the content warrants it) a chart.

### Design decisions

- **The mapping pass is where within-deck variety is decided.** It assigns each slide a layout archetype from the design family's catalogue, such that across the deck the layouts are distributed (a 12-slide deck might use 7–8 distinct archetypes). Type, color, and tone stay constant — that is the "cohesion plus variety" decision from `v1/spec.md`.
- **The mapping pass is schema-validated.** It emits a `Deck`; the model cannot emit presentational values.
- **The mapping pass owns the through-line.** It is what makes a deck read as one authored thing rather than a collage — the narrative arc, the section structure, the call-to-action placement.
- **Charts are spec'd here, built in the slide builder.** The mapping decides *what* a chart says; the builder decides *how* it looks. In v1 charts are simple (bars, lines, donuts) rendered in the deck; the full chart system is v2.

## Verify

- [ ] A mapping produces a schema-valid `Deck` from an approved outline
- [ ] Across a 12-slide deck, the layout archetypes are distributed (no repeated frame)
- [ ] The mapping preserves the narrative through-line and claim provenance
- [ ] **Human:** a mapping of a sample outline reads as a deck a presenter would actually give

## Skipped

- Complex chart types (scatter, heatmap, geographic) — v2
- Per-slide layout *generation* (the model designing a brand-new layout) — v2. v1 uses a curated archetype catalogue

## Exit gate

- [ ] Mapping emits a schema-valid `Deck` with distributed layouts
- [ ] Through-line and claim provenance preserved
