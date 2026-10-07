# Phase 37 — beautiful data

> This phase makes true that when a deck has numbers, they become the most beautiful thing on the slide: the right form for what the number must say, drawn in the deck's own look, labelled on the data, every value traceable to a source — and charts appear whenever the facts can carry one, not once in a blue moon.

**Depends on:** 25 (charts from approved facts), 36 (generated, novel compositions) · **Blocks:** gate 2's wall · **Spec step:** Bets → facts; Commitments → components · **Size:** M · **Owner's ask:** 2026-10-05 — "where are graphs… beautiful graphs… show data"

## Why charts are rare and plain today

| Today | Why |
|---|---|
| None of the 2026-10-05 recordings has a chart | The storyline proposes one only when it holds three numbers for the same measure, and research seldom brings back a series |
| Four forms only (bar, column, line, donut) | A single number is drawn as a stat, a trend as a line, and nothing else; part-to-whole uses a donut, which reads worse than a stacked bar |
| Every chart looks the same | Fixed geometry, fixed label positions, one colour order |
| Colour-blind safety is assumed | The series colours are contrast-checked against the ground, but never against each other under colour-vision deficiency |

## The method

From the dataviz guidance this project adopts (the bundled `dataviz` skill): **pick the form by the data's job, then colour, then validate the colour by running the validator, not by eye.**

| The number's job | Form |
|---|---|
| One value is the point | **Hero figure** — huge, in the display face, with its unit and source; not a one-bar chart |
| A few headline values | **Figure row** (stat tiles) |
| Change over time | **Line**, or **area** for one series; the latest value labelled at the end |
| One item is the story, the rest context | **Emphasis** — the item in the accent, the rest in a quiet ink; the most under-used form |
| Compare magnitudes | **Bar / column**, sorted, labelled on the bars |
| Part of a whole | **Stacked bar** (horizontal for long names) — replaces the donut |
| Before → after per item | **Dumbbell / slope** |
| Above or below a target | **Diverging bar**, or a line against a baseline |
| A share out of 100 | **Waffle / unit grid** — 100 squares, the share filled |

**Non-negotiables:** one axis, never two; series colours in a fixed order, never cycled; more than five series fold into "Other" or small multiples; labels and values in text tokens, never in the series colour; selective direct labels, never a number on every point; recessive gridlines; a legend only when two or more series cannot be labelled directly.

## Make

- **More charts, honestly.** Research gains an evidence need for **series** — the same measure across years or categories — and the storyline is asked to use one wherever the facts allow. A chart still appears only when every value is an approved fact.
- **The planner picks the form by job** (the table above) from the slide's facts, not by habit.
- **`components/charts.py` v2:**
  - the forms above, hand-written SVG, no chart library;
  - drawn in the deck's identity: its display face for figures, its text face for labels, its rule weight for axes, its radius for data ends, its accent for emphasis;
  - **generated, like every composition (phase 36):** orientation, label placement, figure scale and annotation position vary per chart within the rules — two charts of the same data in two decks do not look alike;
  - **annotations:** one short callout where the story is ("2× in three years"), drawn from the facts, never invented;
  - the source line under every chart, from its facts.
- **Series colours generated per deck, then validated:** categorical steps derived from the deck's palette, checked by the dataviz validator (adjacent-pair colour-blind ΔE ≥ 8, normal-vision floor, contrast against the ground), stepped until they pass. Texture as the backup channel for colour-blind readers and print.
- **Accessibility in the export:** every chart carries a visually hidden data table, and its values are in the speaker notes.
- **QA:** labels measured like text (E1–E5 apply to chart labels); a new check that no chart label overlaps a mark.

### Design decisions

- **The data is the visual.** The owner's reference decks are strongest where a real number is huge. A chart earns its place only when it says more than the figure would.
- **Beautiful means legible first.** Thin marks, generous space, one emphasis, direct labels — the dataviz rules are the floor, the deck's look is the voice.
- **A chart is never a picture of data.** It is drawn from approved facts by code; the model only places the empty `<dd-chart>`.

## Verify

- [ ] Golden files for every form, under three generated identities
- [ ] The validator passes for every generated series palette over 1,000 identities (light and dark grounds)
- [ ] Every chart value traces to an approved fact (a test walks the bench)
- [ ] No chart label overlaps a mark or leaves the safe area (QA)
- [ ] **Bench:** at least one chart in every deck whose facts can carry one; none in decks whose facts cannot
- [ ] **Human:** a wall of 20 data slides — the owner rates them at least as good as the 2026-10-05 reference decks, and finds no two that look alike

## Skipped

- Interactive hover in the exported deck — trigger: users send decks that are read on screen, not presented. A projected slide has no cursor.
- Maps and choropleths — trigger: a brief needs geography.
- Charts from an uploaded spreadsheet — trigger: three user requests (it needs an isolated parser).

## Exit gate

- [ ] Charts on every bench deck that has a series in its facts
- [ ] Zero dual axes, zero cycled colours, zero validator failures
- [ ] The owner's data wall passes

## Sprint status (2026-10-08) → [master-plan.md](master-plan.md)

The 36-deck run put charts in 33 of 36 decks, but most were **two values drawn as two bars**.

**Build day (B7, P0):** a **"pair" form** — two values become two large figures in the display face with the change between them ("70% → 58%", "−12 pts"), the form chosen automatically for two points. **Test day:** the data wall is part of the main wall (T5).
