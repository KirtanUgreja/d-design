# New Primitives

Seven here, taking the library from 11 to 18 — plus `Chart`, reversed out of the refusal list below and specified in [plan/16-charts.md](plan/16-charts.md), which makes **19**. Chosen for the product-launch wedge specifically, not for general expressiveness.

**The v1 invariant still holds without exception:** no presentational values. No sizes, no colors, no durations, no speeds. Marquee speed comes from the motion vocabulary. Gallery spacing comes from the rhythm tokens. If a new primitive seems to need a visual prop, the art direction has a gap — fill the gap.

**Cost warning:** 18 primitives × 3 art directions = **54 design surfaces**, and `Chart`'s five marks add 15 more. This is the single largest expense in v2, larger than the art direction system itself. Build these last, in order of real demand, and be willing to ship v2 with 14.

**Two platform notes that apply across several of these.** `Marquee` and `ScrollSequence` are both scroll-linked, and CSS scroll-driven animations (`animation-timeline`, `scroll-timeline`, `view-timeline`) are ~84% supported but **not Baseline** — Firefox stable still gates them behind a flag. Use them as progressive enhancement over the Motion-driven path, and always author the finished state as the default so an unsupported browser shows a complete page rather than a blank one. See [../v1/art-direction.md](../v1/art-direction.md).

Every text-bearing primitive inherits `text-wrap: balance` on headings and `pretty` on body copy from the renderer — see the typography section in [art-direction-system.md](art-direction-system.md). `Timeline`, `Comparison`, and `SpecTable` benefit most, since they set many short strings where a two-word orphan is most visible.

**Every asset-bearing primitive selects by id from `list_assets()`.** `Gallery`, `LogoWall`, `Comparison`, and `ScrollSequence` all reference uploads the user actually made — the AI never composes a URL or invents an asset ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)). An `assetId` that resolves to nothing is a validation failure, not a broken image on a launch page.

**And every one of them is authored in logical properties.** `Gallery`'s `stagger`, horizontal `Timeline`, `Comparison`'s two columns, and `Marquee`'s direction are the four places a physical `left`/`right` will feel natural to write and will cost an audit in v3 ([../v3/localization.md](../v3/localization.md)). `Marquee` and horizontal `Timeline` are on the short list of things that must invert explicitly under RTL, because they move on the x-axis and `transform` ignores logical direction.

---

## Gallery

```ts
Gallery {
  assetIds: string[];                       // 2–8
  layout: 'row' | 'grid' | 'stagger';
  captions?: string[];
}
```

Multiple images as one composed unit. `stagger` offsets alternate items vertically — the editorial move that makes three product shots look art-directed rather than pasted.

## Timeline

```ts
Timeline {
  items: { label: string; title: string; detail?: string }[];   // 2–6
  orientation: 'vertical' | 'horizontal';
}
```

Roadmaps, launch phases, company history. `label` is the time marker ("Q3", "2019", "Phase 1"); `title` is what happened.

Six items maximum. A seven-item timeline is a table, and it should look like one.

## Comparison

```ts
Comparison {
  mode: 'before-after' | 'versus';
  left:  { label: string; assetId?: string; points?: string[] };
  right: { label: string; assetId?: string; points?: string[] };
}
```

`before-after` renders as a draggable image reveal. `versus` renders as two columns of claims.

The single most-requested marketing structure, and the easiest to make look cheap. `versus` in particular needs real design attention per AD — competitor comparison tables are where good design goes to die.

## Marquee

```ts
Marquee {
  items: string[] | { assetIds: string[] };
  direction: 'left' | 'right';
}
```

Continuously scrolling band of text or logos. **Speed is not a prop** — it comes from the motion vocabulary, so `mechanical-snap` scrolls differently from `cinematic-slow` and the AD stays coherent.

Pauses on hover. Respects `prefers-reduced-motion` by rendering as a static row.

## LogoWall

```ts
LogoWall { assetIds: string[]; label?: string }   // 3–12
```

Customer logos, integration partners, press. Static grid — distinct from `Marquee`, which moves.

Boring, and asked for on day one by every marketer. Logos arrive in wildly inconsistent sizes and colors, so each AD must define its own normalization: `mono` treatment, optical sizing, consistent bounding box. Do not skip that; a logo wall with mismatched weights looks broken to everyone and nobody can say why.

## SpecTable

```ts
SpecTable {
  rows: { label: string; value: string }[];        // 2–10
  groups?: { title: string; rowIndices: number[] }[];
}
```

Product specifications, dimensions, technical details. `value` is a string — `"48 hours"`, `"< 50ms"`, `"USB-C"`.

The unglamorous half of a product launch. Under `editorial-light` it should read like a well-set spec sheet; under `bold-brutalist`, like a manifest.

## ScrollSequence

```ts
ScrollSequence {
  assetIds: string[];                              // 12–120 frames
  label?: string;
}
```

Scroll-driven image sequence — the product-rotation move. **The highest-impact primitive here and the one that sells the category.**

It also carries real costs, and they must be handled rather than discovered:

- **Payload.** 120 frames is tens of megabytes. Require dimension caps, serve compressed, lazy-load beyond the first frames.
- **Preloading.** Scrubbing an unloaded sequence looks broken. Block scroll-linking until a threshold of frames is decoded, and show progress.
- **Slides mode.** No scroll means no sequence. Degrades to a single representative frame; the editor warns on mode switch. See [transformations.md](transformations.md).
- **Reduced motion.** Renders as one static frame, not a sequence.
- **Authoring.** Users rarely have a frame sequence lying around. v2 accepts an uploaded video and extracts frames server-side; without that, this primitive goes unused.

**That last bullet adds a video decoder to the project, which is a security decision as much as a feature one.** Video containers and codecs are the same hostile-bytes class as PDFs and image decoders, and the rule already exists: anything parsing untrusted bytes runs in the fetch worker — no database, no VPC route, nothing worth stealing ([../coderules/README.md](../coderules/README.md) rule 5, [../techstack/backend.md](../techstack/backend.md)).

Caps go **before** the decode, not after: byte size, duration, resolution, and frame count. A decoder that has already allocated against a crafted file is a decoder you have already lost. The extracted frames then take the ordinary upload path — magic-byte verification, re-encode, quarantine prefix until clean ([../techstack/infrastructure.md](../techstack/infrastructure.md)).

Ship this one last. It is the most impressive and the most likely to be half-built.

---

## Not added, and why

| | Why not |
|---|---|
| ~~**Charts**~~ | **Reversed 2026-08-09 — see below.** The refusal was about a charting *tool*, and two of its three objections do not survive contact with a chart *primitive*. Built in [plan/16-charts.md](plan/16-charts.md) |
| **Forms / capture** | Collects data, needs a backend, crosses the not-an-app boundary |
| **Embed / iframe block** | Arbitrary third-party content defeats both the art direction and the sandbox guarantee |
| **Accordion / tabs** | Interactive disclosure is app UI. A presentation reveals by scrolling, not by clicking to expand |
| **Map** | Needs a provider, an API key, and network access from inside the page |

The pattern: anything needing network access, persistence, or user input is the boundary being tested. The answer is no, and the reason is the same each time — `Slot` exists for genuine one-offs, sandboxed and unable to do any of it.

### The chart reversal, in full

The original entry read *"a product inside the product: data model, editor, its own design system."* Taken one at a time:

**Data model** — 1–4 series of labelled numbers, 2–12 points each. Smaller than `SpecTable`'s. The objection was imagining a chart that accepts arbitrary shapes; this one does not.

**Editor** — there isn't one. Values are edited through the same property panel and the same AI-edit path as every other block's props. A spreadsheet surface remains refused and always will be; that is the thing the objection was actually about.

**Its own design system** — this one was correct, and it is the reason to build the primitive *here* rather than reach for a library later. Every charting library ships a palette, a grid, a tick style and a legend, and those would be **the one part of a published page the art direction does not control** — Recharts defaults sitting inside `bold-brutalist`, immune to reskin. Rule 12 does not have an exception for third-party components. So: no library, five marks, roughly two hundred lines of SVG, every value a token.

**What actually changed** is that `Stat` covers a number and does not cover a trend, a comparison or a share, so a launch page needing one gets a paragraph describing it instead. And [plan/14-texture-without-gradient.md](plan/14-texture-without-gradient.md) supplied the missing piece: with gradients banned and a nine-role palette, four distinguishable categorical colours do not exist — so series differ on **two token colours × three texture fills**, which survives greyscale and every form of colour blindness because it never carried the distinction on hue. A constraint imposed for one reason solving an unrelated problem is the same signal the character budget gave, and it is the strongest evidence available that the abstraction is right.

**The line that keeps this from becoming a charting tool is drawn at the data, not the visuals.** A `Chart` whose points do not trace to a proof point in the approved Brief is rejected before storage, and `source` is a required field. That is rule 21, and it exists because the failure mode that matters is not an ugly chart — it is a plausible chart of invented numbers on a customer's launch page under their logo.
