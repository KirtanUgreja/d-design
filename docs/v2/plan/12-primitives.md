# Phase 12 — Seven primitives

> 11 blocks becomes 18. Eighteen primitives × three art directions is **54 design surfaces**, which is the single largest cost in v2 — larger than the art direction system itself. Build them in demand order and be willing to ship v2 with fourteen.

**Depends on:** [04](04-three-art-directions.md) · **Blocks:** — · **Spec step:** 13

---

## Search

**Read first**

- [../primitives.md](../primitives.md) — all seven, their props, and "Not added, and why". The refusals matter as much as the additions
- [../../v1/scene-schema.md](../../v1/scene-schema.md) — how a block is added: Pydantic, then generated Zod, then a renderer component, then the property panel gets its controls for free
- [../../v1/plan/04-renderer.md](../../v1/plan/04-renderer.md) — the region model and how a block lands in a layout

**Grep for**

- `api/schema/scene.py` — the discriminated union and its `type` field. v1's truncation defect was caused by that discriminator being serialized last; **any change to the union's shape must keep `type` first** in `serialize_deterministically`
- `web/src/features/editor/controls.ts` — the property panel is generated from the schema. A new block gets controls with no editor work, and if it does not, its props are shaped wrong
- `api/features/generation/tools.py` — `list_assets`. Every asset-bearing primitive selects by id from it; the AI never composes a URL
- `web/src/features/renderer/blocks/visual-seed.ts` — `mulberry32`, `INTENSITY`, `seedFromId`. Anything needing determinism uses these rather than a second PRNG

**Verify externally**

- Scroll-driven animation support. `animation-timeline` / `scroll-timeline` are ~84% and **not Baseline** — Firefox stable still gates them. `Marquee` and `ScrollSequence` use them as progressive enhancement over the Motion-driven path, never as the floor

---

## Make

Build in demand order. **The order is the deliverable**, because the phase is expected to be cut short.

```
1. LogoWall        boring, asked for on day one by every marketer
2. SpecTable       the unglamorous half of a product launch
3. Timeline        roadmaps, launch phases
4. Gallery         multiple images as one composed unit
5. Comparison      most-requested, easiest to make look cheap
6. Marquee         scroll-linked, needs the motion vocabulary
7. ScrollSequence  the one that sells the category, and the one most likely to be half-built
```

### The v1 invariant holds without exception

**No presentational values.** No sizes, no colours, no durations, no speeds. `Marquee`'s speed comes from the motion vocabulary. `Gallery`'s spacing comes from the rhythm tokens. If a new primitive seems to need a visual prop, **the art direction has a gap — fill the gap.**

That sentence is the one most likely to be violated in this phase, because seven new components is seven new opportunities for a `gap` prop that "just needs to be a bit tighter here".

### Three rules that apply across several of them

**Assets are selected by id.** `Gallery`, `LogoWall`, `Comparison` and `ScrollSequence` all reference uploads the user actually made. An `assetId` that resolves to nothing is a validation failure, not a broken image on a launch page — `assert_assets_resolve` already exists and extends to the new fields.

**Logical properties, always.** `Gallery`'s stagger, horizontal `Timeline`, `Comparison`'s two columns and `Marquee`'s direction are the four places a physical `left`/`right` will feel natural to write and will cost an audit in v3. `Marquee` and horizontal `Timeline` **must invert explicitly under RTL**, because they move on the x-axis and `transform` ignores logical direction.

**Typography comes from the renderer.** `text-wrap: balance` on headings, `pretty` on body copy. `Timeline`, `Comparison` and `SpecTable` benefit most — they set many short strings, where a two-word orphan is most visible.

### `LogoWall` — the boring one with the real trap

Logos arrive in wildly inconsistent sizes and colours. **Each art direction must define its own normalization**: mono treatment, optical sizing, a consistent bounding box. Skipping it produces a wall that looks broken to everyone and that nobody can articulate.

That normalization is a token, not a component branch. It is the most likely place in this phase for rule 12 to be broken by accident.

### `ScrollSequence` — ship it last, and it carries a security decision

The highest-impact primitive and the one most likely to be half-built. Its costs must be handled rather than discovered:

- **Payload.** 120 frames is tens of megabytes. Dimension caps, compression, lazy-load beyond the first frames
- **Preloading.** Scrubbing an unloaded sequence looks broken. Block scroll-linking until a threshold of frames is decoded, and show progress
- **Slides mode.** No scroll means no sequence. One representative frame, and the editor warns on mode switch ([10](10-slides-mode.md))
- **Reduced motion.** One static frame, not a sequence
- **Authoring.** Users rarely have a frame sequence. v2 accepts an uploaded video and extracts frames server-side — **without that, this primitive goes unused**

**That last bullet adds a video decoder, which is a security decision as much as a feature one.** Video containers and codecs are the same hostile-bytes class as PDFs and image decoders, and the rule already exists: anything parsing untrusted bytes runs in the **fetch worker** — no database, no VPC route, nothing worth stealing.

**Caps go before the decode, not after:** byte size, duration, resolution, frame count. A decoder that has already allocated against a crafted file is a decoder you have already lost. The extracted frames then take the ordinary upload path — magic-byte verification, re-encode, quarantine prefix until clean.

If the fetch worker does not exist yet when this phase arrives, **`ScrollSequence` does not ship.** Running a video decoder in `api` is the one placement the dependency rules say should feel wrong, and feeling wrong is the whole signal.

### What is refused, and why the list is part of the design

Charts · forms · embed/iframe · accordion/tabs · maps. The pattern: **anything needing network access, persistence, or user input is the boundary being tested.** The answer is no, and the reason is the same each time — `Slot` exists for genuine one-offs, sandboxed and unable to do any of it.

---

## Verify

**The gate** — green, schema regenerates with no diff for every block added.

**Per primitive, before moving to the next**

- [ ] Renders under **all three art directions**. This is the 54-surface cost and it is paid per block, not at the end
- [ ] The property panel generated controls for it with no editor code
- [ ] No presentational value in its props. The invariant test walks the new block and still passes
- [ ] Logical properties throughout; correct under `dir="rtl"`
- [ ] `prefers-reduced-motion: reduce` degrades it sensibly
- [ ] Its text fields respect the current art direction's budgets

**Schema**

- [ ] `type` still serializes first in the discriminated union. v1's truncation defect came from it serializing last, and seven new variants is seven new chances to reintroduce it
- [ ] Every asset-bearing field goes through `assert_assets_resolve`
- [ ] A golden brief generates at least one of the new primitives without prompt surgery. A primitive the pipeline never chooses is a primitive with no reason to exist

**Security** ([../../security/testing.md](../../security/testing.md))

- [ ] The injection corpus runs with the new primitives available. No `Marquee` item, `SpecTable` value or `Comparison` point carries an instruction, a URL the brief did not supply, or a prompt fragment
- [ ] `LogoWall` and `Gallery` reject an `assetId` the caller does not own — fails closed, on ownership
- [ ] If `ScrollSequence` ships: video caps are enforced **before** decode, the decoder runs in the fetch worker, and a crafted file is rejected rather than absorbed

**Human — this is the phase**

- [ ] All 18 primitives under all 3 art directions, looked at. 54 surfaces, and it is the real cost of v2
- [ ] `Comparison`'s `versus` mode under each art direction. Competitor comparison tables are where good design goes to die, and this one needs real attention per art direction
- [ ] A `LogoWall` with deliberately mismatched logos. If it looks broken, the normalization tokens are missing

---

## Skipped

| Not built | Trigger |
|---|---|
| Charts | Still a product inside the product. `Stat` covers marketing needs |
| Forms / capture | Collects data, needs a backend, crosses the not-an-app boundary |
| Embed / iframe block | Arbitrary third-party content defeats both the art direction and the sandbox guarantee |
| Accordion / tabs | Interactive disclosure is app UI. A presentation reveals by scrolling |
| Map | Needs a provider, an API key, and network access from inside the page |
| Any primitive after the cut line | Real demand. **Shipping v2 with fourteen primitives is an acceptable outcome**, and the demand order above is what makes that a decision rather than an accident |

---

## Exit gate

- [ ] Every primitive that shipped renders under all three art directions, in both modes, LTR and RTL
- [ ] No new presentational prop anywhere; anything that wanted one became a token
- [ ] `type` still serializes first, and the golden briefs still pass
- [ ] Every asset field resolves through ownership and fails closed
- [ ] `ScrollSequence` either ships with pre-decode caps in the fetch worker, or does not ship
- [ ] The primitives that were cut are recorded here with the demand signal that would build them
- [ ] The gate is green
