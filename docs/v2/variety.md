# Variety

The product's central promise is that no two decks look alike. This document is the only place that promise is treated as a **measurable claim** rather than an aspiration, because it was asserted for three releases and never once counted.

**It was counted on 2026-08-10. The plan as written does not keep the promise.** What follows is the measurement, the two reasons it fails, the four fixes, and the gate that makes it checkable from now on.

## The measurement

Run against the three shipped art directions and the schema, not estimated:

| Axis | Values available | Kind |
|---|---|---|
| **Font families** | **6** — Fraunces, Inter, Newsreader, Archivo, Syne, Space Grotesk | discrete, tiny |
| **Layouts** | **6** — full-bleed, split-left, split-right, centered, stack, grid | discrete, tiny |
| **Texture kinds** | **6** — grain, halftone, hatch, dither, weave, rule | discrete, tiny |
| **Scene intents** | 5 — hook, problem, reveal, proof, cta | discrete |
| **Motion intents** | 4 — reveal, emphasize, parallax, none | discrete |
| **Colour** | continuous | pruned hard by the contrast linter and the brand kit |
| **Rhythm / scale** | continuous | the least visible axis to a non-designer |

And the finding that should be uncomfortable:

> **53% of an art direction is byte-identical across all three.** Of 236 distinct value paths, only 112 differ between `cinematic-dark`, `editorial-light` and `bold-brutalist` — the three most deliberately distant points anyone has built in this format. Half of every art direction is not a choice; it is the format's shared skeleton.

### The competitive frame, stated plainly

Gamma ships **25+ themes**. Canva ships **250,000 templates**. This product ships **three art directions**, and the bet is that *generated* beats *curated*.

**Right now that bet loses on arithmetic.** A generator bounded by 6 fonts and 6 layouts has a smaller reachable space than Gamma's curated 25. Being generative is not automatically being various.

## Failure 1 — the engine generates on the wrong axis

The two things that carry the most visual identity in graphic design are **typeface** and **layout structure**. A person who cannot name a font can still tell two decks apart by their type and their composition. Colour is the axis they attribute to *"the brand"* — and in this product colour largely **comes from** the brand kit anyway.

Those two identity-carrying axes are the **smallest and most discrete** in the system: six each. Colour and rhythm — the continuous axes with real headroom — are the ones the art-direction engine spends its intelligence on.

> **Generating a fourth palette does not fix sameness when every deck shares one of six typefaces and one of six layouts.**

This is the mechanical reason three generated art directions will collide exactly as three hand-authored ones do, and it is independent of how good the model is.

## Failure 2 — the model will not supply the diversity

The plan asks an LLM to produce three distant art directions as **structured JSON against a fixed schema**. That is the worst case for output diversity, and it is documented rather than speculative:

- **Mode collapse is the norm, not the exception.** LLMs converge to a narrow output space — an *"Artificial Hivemind"* — along two dimensions: **intra-model** (repeated samples converge to the same ideas) and **inter-model** (independently trained models produce similar responses). Three candidates from one prompt is exactly the intra-model case
- **Structured output makes it worse.** Instruction tuning with rigid format templates induces *diversity collapse*; format tokens measurably reduce semantic and lexical diversity. The AD schema is a rigid format template
- **The obvious mitigations do not work.** Raising sampling temperature and adding "be diverse" instructions produce **negligible effects** compared to structured interventions. Temperature raises token-level diversity without raising semantic diversity, and costs quality on the way
- **Training data is biased toward Western, mainstream stylistic norms**, so the collapse is not toward a random point — it is toward the same tasteful default every other tool lands on

**The consequence, stated at full strength:** ask a model for three art directions and you get three variations on one idea, *and you get the same idea for every user*. The shelf does not disappear. It moves inside the model, where you cannot see it, cannot count it, and cannot fix it by authoring.

That is a worse position than the hand-authored shelf, because at least a shelf is honest about its size.

## What is *not* the fix

**Component and UI libraries.** Proposed on 2026-08-10 as a way to buy creative range: combine shadcn, Canvas UI, Watermelon UI and others, and let the engine assemble the best of each.

It is refused, and the reason is that it is the disease presented as the cure.

- **A component library is a shelf, one level down.** Every SaaS site currently looks identical *because* they all import the same components. Building on five libraries buys the sameness problem permanently, in `node_modules`, where no art direction can reach it
- **It ends reskin.** A library component carries its own spacing scale, type ramp, radii and colour semantics — design the art direction does not own. Restyling five vocabularies is not N tokens, it is N×M overrides, and *"any AD works with any deck"* becomes false the moment one lands
- **It is already ruled on.** [spec.md](spec.md): *"the moment an AD can add a layout or a component, 'any AD works with any experience' becomes a lie."* Charts were refused a library on the same grounds — *"a library would be the one part of a page the AD does not control"*
- **Mixing systems is not range, it is incoherence.** Five libraries encode five designers' tastes at five different spacing scales. The output reads as assembled from parts, which is the exact defect [plan/17-composition.md](plan/17-composition.md) exists to fix
- **They solve a problem this product does not have.** Those libraries are built for apps — dropdowns, modals, data tables, forms. A slide has almost none of that

**Two carve-outs, and they are real rather than consolation:**

| Allowed | Why |
|---|---|
| **Any library in our own chrome** — editor, marketing site, app UI | [../design/README.md](../design/README.md) is explicit that our surfaces are not the artifact. shadcn in the editor is ordinary and fine |
| **Headless libraries in the artifact** — Radix, Base UI, Ark UI | They supply behaviour and accessibility with **zero visual opinion**, so there is no styling to fight and rule 7 is untouched. This is the door if a slide ever needs real interactive components |

And the third thing, which is not a carve-out but is the actual advice: **study what those libraries do well and rebuild the good parts as AD-controlled primitives.** Slower per feature. The only version that compounds.

## The four fixes

Ranked by variety gained per unit of work.

### 1. Widen the font registry — 6 families to 40+

**The highest-leverage change available, and it is mechanical rather than clever.** Typography carries more identity than any other axis and it currently has six values.

- **Legally clear.** The SIL Open Font License explicitly permits bundling and embedding in commercial products, including SaaS, provided the font files are not sold on their own. Most high-quality display faces worth having are OFL
- **Free at runtime.** Only two families ship per deck, so a 40-family registry costs storage, not bundle size — including in [plan/20-offline-and-export.md](plan/20-offline-and-export.md)'s one-file download
- **Curated pairs, not arbitrary combinations.** 40 families is not 1,560 pairs; it is a few hundred *vetted* pairs, authored the same way the existing three were. This is where the taste bottleneck goes, and it is a far better use of hand-authoring time than a fourth complete art direction

Rough arithmetic on distinguishable looks, before colour: today ~12 tasteful pairs × 2 ground polarities × 6 texture kinds ≈ **144**. At 40 families: ~200 pairs × 2 × 6 ≈ **2,400**. That is the difference between *fewer looks than Gamma* and *a real answer*. Phase [24](plan/24-font-registry.md).

### 2. Diversity from a sampler, not from the model

**Stop asking the model to be various. Ask it to be good.**

The discrete, identity-carrying axes — font pair, ground polarity, texture kind, layout bias, motion vocabulary — are chosen by a **structured sampler** that guarantees three candidates land in genuinely distant regions. The model then fills the continuous values, adapts to the brand, and justifies its choices, inside the region it was handed.

This is precisely what the research says works: *structured interventions* beat temperature and prompt instructions, and different structural interventions cover **distinct regions of the space** where sampling one prompt three times does not. It also makes diversity **auditable** — you can measure the distance between three candidates before rendering them, which you can never do with three samples from a prompt.

**Distance is enforced, not hoped for.** Two candidates sharing a font pair *and* a ground polarity are not two candidates. Phase [21](plan/21-art-direction-engine.md).

### 3. Widen composition — six layouts is the second ceiling

Six fixed layouts is the other small discrete axis, and unlike fonts it cannot be widened by adding rows to a registry. It needs layouts to become **parametric** — split ratios as tokens rather than `1fr 1fr`, offset and asymmetric grids, and where the anchor sits within the frame.

The pivot to slides makes this tractable for the first time: composition needs a bounded frame to be checkable, and [plan/18-presentation-frame.md](plan/18-presentation-frame.md) provides one. Phase [17](plan/17-composition.md).

### 4. Seed from the content, because there is no such thing as no input

A user who supplies no brand and no reference has still supplied a Brief: an industry, a tone, an audience, stakes, and their own word choices. A biotech Series A, a coffee launch and a games studio pitch should not resolve to the same region of the space, and nothing about that requires the user to say one word about design.

**The sampler is seeded from the content**, so different subjects land in different regions deterministically — and the same brief twice lands in the same place, which is also correct. Phase [21](plan/21-art-direction-engine.md).

## The gate

> **Ten briefs from ten unrelated industries, with no brand kit and no reference. Generate three candidates each. Put all thirty on one wall. If any two could be mistaken for each other, the release has failed.**

Two things make this a real gate rather than a ritual:

**It is measurable before it is judged.** The sampler's axes are enumerable, so *"these two share a font pair and a ground"* is a computed failure, not an opinion. The eye is for what the numbers cannot see; the numbers stop the obvious failures reaching the eye.

**It is the investor answer.** The honest claim is not *"our tool is infinitely creative."* It is *"thirty decks, ten industries, zero design input, no two alike — here is the wall."* That is checkable, and it is the more credible sentence.

## What this document cannot fix

**Curation is still one person, and that does not change.** Every fix above moves the bottleneck rather than removing it: font *pairs* are curated, sampler *regions* are curated, layout *parameters* are bounded by taste. The engine amplifies one person's judgement across thousands of decks. That is the moat and the ceiling, and it is the same fact seen from two sides.

**None of this is proven until decks exist.** Every number here is a property of the schema, not of output anybody has looked at. The mode-collapse research says the model will disappoint; the sampler is the answer to that, and it is untested. **Do not treat this document as reassurance.** It is a hypothesis with a gate attached, and the gate is the only part that will tell the truth.

**The wall test can pass and users can still feel sameness.** Thirty decks that a designer can tell apart may still read as one product to someone who sees two of them a month apart. If that happens, the axis to widen next is narrative structure — five `SceneIntent` values and one deck archetype — and nothing in this document addresses it.
