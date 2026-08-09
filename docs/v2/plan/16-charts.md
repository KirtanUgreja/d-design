# Phase 16 — Charts

> Refused twice, in v1 and again in v2, on the grounds that real charting is a product inside the product. That reasoning was about a *charting tool*. This builds a chart **primitive** — five marks, no data editor, no library, and numbers that have to come from somewhere.

**Depends on:** [04](04-three-art-directions.md), [14](14-texture-without-gradient.md) · **Blocks:** — · **Spec step:** delta — see [../spec.md](../spec.md) → "Composition deltas"

---

## What changed about the refusal

[../primitives.md](../primitives.md) → "Not added, and why" reads: *"Charts — still a product inside the product: data model, editor, its own design system. `Stat` covers marketing needs."*

Two of those three objections were about a feature nobody proposed, and the third was the real one.

| Objection | Answer |
|---|---|
| **Data model** | 1–4 series of labelled numbers. It is `list[list[float]]` with names, and it is smaller than `SpecTable`'s |
| **Editor** | There isn't one. Values are edited through the same property panel and the same AI edit path as every other block's props. A spreadsheet is the thing being refused, and it stays refused |
| **Its own design system** | This is the real objection, and it is also the reason to build it here rather than later. Every charting library ships a design system, and it would be **the one part of a published page the art direction does not control** — a Recharts default palette sitting inside `bold-brutalist`. A chart that reads tokens is a chart the reskin promise still covers |

`Stat` genuinely does cover a single number. It does not cover a trend, a comparison, or a share, and a product-launch page that needs one of those currently gets a paragraph describing it. That is the gap.

**The line that keeps this from becoming a charting tool** is drawn at the data, not at the visuals: the AI may only emit a chart whose numbers trace to something the user supplied. See "Numbers have to come from somewhere" below. Everything else here is a rendering problem with a token layer already attached.

---

## Search

**Read first**

- [../primitives.md](../primitives.md) → the whole file, and "Not added, and why" specifically. The invariant at the top governs this primitive without exception: no sizes, no colours, no durations
- [../../design/principles.md](../../design/principles.md) → principle 5, the row *"Counting-up stat numbers with no source — theatre"*, and principle 10. A chart with no provenance is the same theatre with a bigger canvas
- [14](14-texture-without-gradient.md) → the texture vocabulary. Series are differentiated by texture as well as hue, and that is not decoration
- [../art-direction-system.md](../art-direction-system.md) → "The AD linter". Chart tokens are linted like every other token group

**Grep for**

- `web/src/features/renderer/blocks/stat.tsx` — the existing single-number block, its type role, and how it reads `--type-stat-*`. A chart's value labels use the same roles; it does not invent a scale
- `web/src/features/renderer/blocks/list.tsx` — the closest existing precedent for a block with repeated structured children and per-item motion staggering
- `web/src/features/art-direction/art-direction.ts` → `Palette`. Four series come out of a nine-role palette without adding a colour
- `api/schema/scene.py` → the block union and `Scene._structural_rules`. Chart-specific limits belong in a Pydantic validator, next to the grid's 2–4 cells rule
- `docs/coderules/dependencies.md` — **before reaching for a charting library.** Rule 5, and the answer here is no

**Verify externally**

- The `dataviz` skill, before writing a line of mark code or choosing a single colour. Its form heuristic, mark specs and colour formula are the reference this phase is measured against, and re-deriving them by taste is the failure mode
- APCA for a value label sitting on a filled bar — it is text on a coloured surface and gets the same gate as any other text

---

## Make

```
web/src/features/renderer/blocks/
  chart/
    chart.tsx           dispatch on kind, one scale helper, one axis helper
    marks.tsx           bar · column · line · donut · dot
    scale.ts            domain, ticks, and the zero-baseline rule
    chart-a11y.tsx      the visually-hidden table
web/src/features/art-direction/
  art-direction.ts      + ChartTokens
  cinematic-dark.ts · editorial-light.ts · bold-brutalist.ts
api/schema/scene.py     + ChartProps and its validator
api/features/generation/ the proof-point trace
```

### 1. The schema

```ts
Chart {
  kind: 'bar' | 'column' | 'line' | 'donut' | 'dot';
  series: { label: string; points: { label: string; value: number }[] }[];  // 1–4
  valueFormat: 'number' | 'percent' | 'currency' | 'duration';
  unit?: string;                       // "ms", "users" — 12 chars
  emphasis?: { series: number; point?: number };
  caption?: string;
  source: string;                      // required. see below
}
```

2–12 points per series. Every series the same length or it is a validation failure, not a ragged render.

**No colour, no axis config, no size, no orientation beyond `kind`, no legend toggle, no animation setting.** If a chart appears to need one, the art direction has a gap — the same sentence that governs every other primitive.

`emphasis` is the only stylistic-adjacent field and it is intent, not styling: it names *which datum the story is about*, exactly as `Headline.emphasis` names which role a headline plays. The art direction decides what emphasis looks like — a filled bar against outlined ones, a value label appearing, a rule dropped to the axis.

### 2. Series are distinguished by texture, not only by hue

This is the phase's best idea and it falls straight out of [14](14-texture-without-gradient.md).

With gradients banned and a nine-role palette, four categorical colours that are distinguishable, on-brand, and contrast-safe do not exist. Rotating the accent's hue to manufacture them produces exactly the acid palette [14](14-texture-without-gradient.md) bans, and it produces it differently under every art direction.

So series differ on **two axes — two token colours × three fills:**

| Series | Colour | Fill |
|---|---|---|
| 1 | `accent` | flat |
| 2 | `ink` | flat |
| 3 | `accent` | halftone |
| 4 | `ink` | hatch |

Four series, no new colours, nothing near neon, and the differentiation survives greyscale, projection, and every form of colour blindness — because it was never carrying the distinction on hue alone. A pattern fill is normally the accessibility fallback bolted on afterwards. Here it is the primary mechanism and the aesthetic one at the same time, which is the sign the constraint was productive rather than merely obeyed.

`ChartTokens.fills` is per-AD and ordered, so `editorial-light` can use hatch where `bold-brutalist` uses solid blocks.

### 3. The tokens

```ts
interface ChartTokens {
  series: readonly { color: keyof Palette; fill: 'flat' | 'halftone' | 'hatch' }[]; // 4
  grid: 'none' | 'baseline' | 'full';
  gridWeight: Length;
  axisType: TypeRoleKey;               // which type role labels an axis
  valueLabel: 'always' | 'emphasis-only' | 'never';
  markGap: Length;
  markEdge: Length;                    // corner radius. 0 for most
  lineWeight: Length;
  dotSize: Length;
}
```

Three art directions, three genuinely different charts from identical data:

| | `cinematic-dark` | `editorial-light` | `bold-brutalist` |
|---|---|---|---|
| grid | `none` | `full`, hairline | `baseline`, thick |
| axis | none, values labelled directly | hairline both axes, serif ticks | none, giant labels |
| valueLabel | `emphasis-only` | `always` | `always` |
| markEdge | 0 | 0 | 0 |

A chart that looks like a Recharts chart in three colour schemes has failed this phase. A chart that looks like a printed table under one AD and a stage graphic under another has passed it.

### 4. No charting library

Five marks over a linear scale is roughly two hundred lines of SVG. A library is 40–120 kB on a published page, ships its own defaults for every one of the tokens above, and requires fighting those defaults in perpetuity to keep rule 12 true. Rule 5 applies and the ledger line is not written.

**Direct labelling over legends.** A legend is a lookup table between a colour and a meaning, and it is the single most common reason a chart in a presentation is unreadable at the back of a room. Label the series on the mark. `ChartTokens` has no legend field because there are no legends.

### 5. Numbers have to come from somewhere

The failure mode that matters is not an ugly chart. It is a plausible chart of **numbers the model made up**, published on a customer's launch page under their logo.

Three controls:

- **The Build phase may only emit a `Chart` whose points trace to a proof point in the approved Brief.** Not "should" — the generation path carries the trace and a chart without one is rejected before it reaches storage, the same way an `assetId` that resolves to nothing is a validation failure and not a broken image
- **`source` is required**, not optional. There is no chart in this system without a line saying where the numbers came from. Principle 5 already calls an unsourced stat number theatre; the only thing this adds is a schema field that makes it unrepresentable
- **The editor shows the trace.** Selecting a chart shows which proof point each series came from, so a marketer can check it in one look rather than in a spreadsheet

### 6. Honesty rules, enforced in the renderer

The AI supplies the numbers, so the chart's integrity cannot be a prop it sets:

- **Bar and column charts start at zero.** Always. Not a token, not a field, not overridable — a truncated bar axis is a lie and the block is not given a way to tell it
- **Line and dot charts may start elsewhere**, because a trend in a narrow band is a legitimate reading, but the baseline value is always labelled and a non-zero baseline is visibly marked
- **No dual axes, no 3D, no pie.** `donut` takes one series of at most three slices and requires `emphasis`; past three slices the honest form is a bar chart and the schema says so
- **Every axis carries its unit.** `valueFormat` plus `unit`, and a percent series whose points do not sum sensibly is flagged by the linter rather than rendered

### 7. Accessibility is not the caption

- `role="img"` with an `aria-label` composed from the caption, the series labels and the emphasised value
- A **visually-hidden data table** with the real numbers, always rendered. This is also what makes a chart searchable, copyable and readable by anything that is not a browser
- Value labels are text on a filled mark and get the APCA gate, per art direction, at the AD's own fill
- Under `prefers-reduced-motion: reduce`, marks appear at their final state — no growing bars, no drawing lines

### 8. Budgets apply to a chart's strings too

Series labels, point labels, caption and source are copy, and they overflow under a tight art direction exactly as a headline does. Add them to `ContentBudgets`, route them through the same `OverflowReport`, and a 34-character brutalist chart caption becomes the same flagged banner as everything else. One mechanism, now a fifth entry point.

---

## Verify

**The gate** — green.

**The primitive**

- [ ] All five marks render under all three art directions. Fifteen surfaces, and this is the real cost of the phase
- [ ] Identical data under three art directions produces three charts that do not look like the same chart recoloured
- [ ] `assertNoPresentationalValues` passes on `ChartProps`. No colour, no size, no duration reaches the schema
- [ ] Four series are distinguishable **in greyscale** and under a deuteranopia simulation. If they are not, the fill axis is not doing its job
- [ ] No renderer branch on art direction id. The chart is a token consumer like every other block

**Honesty**

- [ ] A bar chart with values 98, 99, 100 renders from zero and looks boring. That is correct
- [ ] A line chart with a non-zero baseline labels it visibly
- [ ] A four-slice donut is a validation error, not a render
- [ ] A chart whose points do not trace to a Brief proof point is rejected in the build path. Test it with a model output that invents plausible numbers — this is the assertion the phase exists for
- [ ] `source` is required by Pydantic and by Zod, and an empty string does not satisfy it

**Accessibility**

- [ ] The hidden data table matches the rendered values exactly, generated from the same array
- [ ] Value labels pass APCA against their own mark's fill, per art direction — including the halftone and hatch fills, where the effective background is not a flat colour
- [ ] Reduced motion renders the final state with no mark animation
- [ ] Keyboard focus reaches the chart and announces the label

**Integration**

- [ ] Chart strings are in `ContentBudgets` and overflow through the existing report
- [ ] A chart in a `fit: viewport` scene from [13](13-scene-fit.md) sizes to the frame without overflowing it
- [ ] Invariants check 8 passes. A chart is the most tempting place in the codebase to reintroduce a gradient fill

**Human**

- [ ] Put a chart on screen and stand at the back of a room. If the series need a legend to read, the direct labelling is wrong
- [ ] Show it to someone who makes decks. The question is whether it looks like a slide from a design studio or a slide from a BI tool

---

## Skipped

| Not built | Trigger |
|---|---|
| Any charting library | Never, while rule 12 holds. The library's design system would be the one part of the page the art direction does not own |
| A spreadsheet-style data editor | The original refusal, and it stands. Values are edited as props |
| Live or connected data | v3 ([../../v3/live-data.md](../../v3/live-data.md)). A chart in v2 is a picture of a number, not a subscription |
| Pie, stacked, area, scatter with regression, dual-axis, sparkline-in-text | Real demand, one at a time. Five marks is already fifteen surfaces |
| More than 4 series or 12 points | It is a table. `SpecTable` is that primitive |
| Interactive tooltips, zoom, brush | A presentation reveals by scrolling, not by hovering — the same reason accordions were refused |
| Importing a CSV | It is the data editor wearing a hat |

---

## Exit gate

- [ ] Five marks, three art directions, no renderer branch and no library
- [ ] Series differentiated by colour **and** fill, legible in greyscale
- [ ] Zero baseline on bars, enforced and not overridable; `source` required by both schemas
- [ ] Charts trace to Brief proof points, and an invented-number output is rejected in the build path
- [ ] Hidden data table, APCA-passing value labels, reduced motion honoured
- [ ] Chart strings budgeted and flowing through the existing overflow report
- [ ] [../primitives.md](../primitives.md) updated — charts move out of "Not added, and why", with the reasoning that changed
- [ ] The gate is green
