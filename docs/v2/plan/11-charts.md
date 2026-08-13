# Phase 11 — charts

> This phase makes true that charts are first-class content — schema-owned, styled by the deck's design system, and generated per-slide like everything else.

**Depends on:** 10 · **Blocks:** 13 · **Spec step:** Locked decisions → charts

## Search

**Read first** — docs/v1/plan/01-schema.md (the `Deck` schema), docs/v1/plan/04-slide-builder.md (per-slide generation), docs/v1/plan/03-mapping.md (charts spec'd in mapping)

**Grep for** — the `chart` block shape in the schema, the slide-builder prompt

**Verify externally** — current state of declarative chart rendering (no heavy chart library in the single-file offline artefact); what a schema-owned chart block looks like

## Make

Charts become first-class blocks: the schema owns a `chart` block (chart type + data + encoding), the mapping pass spec's what a chart says, the slide builder generates the chart's data and encoding, and the renderer draws it with the family's tokens.

### Design decisions

- **Charts are content, not decoration.** The schema owns chart type, data, and encoding. The model emits *what* the chart says; the renderer styles it with the family's color, type, and spacing. The no-styling invariant holds — a chart carries no hex or px.
- **Images are chart companions, not chart replacements.** Where a slide would read better with an image beside the chart (a product hero, an illustration of the data's subject), the slide builder generates one via OpenRouter image models — the same `image` block as v1 (`docs/v1/plan/04-slide-builder.md`). The chart carries the data; the image carries the subject.
- **The single-file artefact stays light.** A declarative chart description rendered by the family's tokens, not a heavy chart library. The chart is drawn by the renderer (SVG), which keeps the offline file self-contained.
- **Charts are generated per-slide.** The slide builder produces the chart block like any other block; the mapping pass decides where a chart earns its place.
- **Chart variety is part of the fingerprint.** A deck that uses the same chart type on every slide is a collapsed deck; the variety gate measures chart-type distribution too.

## Verify

- [ ] The schema owns a `chart` block (type, data, encoding)
- [ ] The renderer draws charts from the family's tokens, no presentational values
- [ ] Charts render in the single-file offline artefact
- [ ] **Human:** a deck with 3–4 charts reads as a designed data story, not a spreadsheet dump

## Skipped

- Interactive charts — v3. v1/v2 charts are static (SVG) in the offline file

## Exit gate

- [ ] Schema-owned chart block
- [ ] Renderer draws charts with family tokens
- [ ] Charts render offline and are fingerprint-measured
