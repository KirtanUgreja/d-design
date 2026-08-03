# New Primitives

Seven, taking the library from 11 to 18. Chosen for the product-launch wedge specifically, not for general expressiveness.

**The v1 invariant still holds without exception:** no presentational values. No sizes, no colors, no durations, no speeds. Marquee speed comes from the motion vocabulary. Gallery spacing comes from the rhythm tokens. If a new primitive seems to need a visual prop, the art direction has a gap — fill the gap.

**Cost warning:** 18 primitives × 3 art directions = **54 design surfaces**. This is the single largest expense in v2, larger than the art direction system itself. Build these last, in order of real demand, and be willing to ship v2 with 14.

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

Ship this one last. It is the most impressive and the most likely to be half-built.

---

## Not added, and why

| | Why not |
|---|---|
| **Charts** | Still a product inside the product: data model, editor, its own design system. `Stat` covers marketing needs |
| **Forms / capture** | Collects data, needs a backend, crosses the not-an-app boundary |
| **Embed / iframe block** | Arbitrary third-party content defeats both the art direction and the sandbox guarantee |
| **Accordion / tabs** | Interactive disclosure is app UI. A presentation reveals by scrolling, not by clicking to expand |
| **Map** | Needs a provider, an API key, and network access from inside the page |

The pattern: anything needing network access, persistence, or user input is the boundary being tested. The answer is no, and the reason is the same each time — `Slot` exists for genuine one-offs, sandboxed and unable to do any of it.
