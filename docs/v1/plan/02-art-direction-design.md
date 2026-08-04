# Phase 02 — Art direction, the design half

> No code. Collect references, hand-design three scenes against real content, and only then derive tokens from what you drew. This is the phase that decides whether the product is worth building.

**Depends on:** [01](01-scene-schema.md) · **Blocks:** [03](03-art-direction-tokens.md) · **Spec step:** 2, design half

[../spec.md](../spec.md), Risk 1: *"Art direction #1 must be genuinely beautiful. If it isn't, the runtime, the pipeline, and the canvas are all worthless. This is a design problem, solo, and the one place AI assistance helps least. Collect reference work before writing tokens."*

That instruction is why this is a separate phase. Tokens written first become a spec you then design *down to*, and the result is competent and forgettable — which is the exact failure the product accuses Gamma of ([../market.md](../market.md)).

---

## Search

**Read first**

- [../art-direction.md](../art-direction.md) — the five token groups, and `cinematic-dark`'s starting values. Starting values, not finished ones
- [../art-direction.md](../art-direction.md) → "Where this gets hard" — type pairing, the hero scene, and how abstract visuals read against real photography
- [../../techstack/frontend.md](../../techstack/frontend.md) → "Fonts" — open licence is a product constraint, not a budget one. These fonts are redistributed to your customers' audiences

**Collect** — 20–30 references, saved as images with a one-line note on what each does that you want:

- Apple product pages — negative space, type scale, restraint at the hero
- Linear's marketing site — density, hairlines, the dark surface hierarchy
- Vercel launch pages — motion pacing, how a stat block earns its size

Then a second, harder set: **three references you think are beautiful and one you think is over-designed.** The fourth is what tells you where your own line is, and `cinematic-dark` lives close to it.

**Verify externally**

- Fontsource catalogue for the display/text pairing. `Instrument Serif` and `Inter` are the documented fallback, not a decision. Audition at least four pairings at hero size against real copy
- That the display face has the weights you are specifying (500 at hero, 600 at stat). A face missing a weight silently substitutes and the whole scale shifts

---

## Make

**Hand-write three scenes as static HTML and CSS.** Not Figma — the values transfer directly into phase 03, and a comp made in the medium it ships in cannot lie about what the browser will do with 8vw type.

| Comp | Uses | Why this one |
|---|---|---|
| **Hero** | `full-bleed` · `Eyebrow` + `Headline(hero)` + `CTA` | First thing anyone sees, and the only thing most people judge. Design it by hand against real content before generalizing to tokens |
| **Proof** | `split-left` · `Headline(section)` + `Body(lead)` + `Stat` ×2 | Where the type scale is tested against a second axis, and where a long body destroys a split layout if the measure is wrong |
| **Statement** | `centered` · `Quote` | Maximum restraint. If this one reads as empty rather than confident, the whole art direction is wrong and it is better to know now |

**Use real content.** Take one actual product launch — yours or a company you admire — and use its real copy. Lorem ipsum hides every length problem the caps in [../scene-schema.md](../scene-schema.md) exist to create.

**Author the comps in CSS logical properties from the first line.** `padding-inline`, `margin-block-start`, `inline-size`. Not because v1 needs it — v1 has no RTL — but because these comps become the tokens, and a physical value written here propagates into every primitive in phase 04 ([../../v3/localization.md](../../v3/localization.md)). It costs nothing now and is an audit of 19 primitives later.

**Then, and only then, extract the tokens.** Read the comps back and write down every distinct value. That list is the input to phase 03. The test of the extraction: **nothing in the comps is a one-off number.** If a value appears once and does not belong to a scale, either the scale is missing a step or the value was arbitrary — resolve which, and do not carry an arbitrary number into a token file.

---

## Verify

This phase's verification is mostly judgment, so the checks that *can* be mechanical are worth doing precisely.

**Mechanical**

- [ ] Every text-on-surface pair in the three comps computes ≥ 4.5:1. Measure it, do not eyeball it. `--ink-muted` at 0.62 alpha and `--ink-faint` at 0.38 are the two that will fail, and it is better to correct the token than to discover the failure in phase 03's resolver
- [ ] `--ink-faint` is used only for non-essential text (eyebrows, captions). If it carries meaning anywhere, it is the wrong role
- [ ] A reduced-motion variant of each comp exists and still reads as designed — not as the comp with the animation removed. [../art-direction.md](../art-direction.md) is explicit that this is a design requirement for this product specifically, because parallax is a documented vestibular trigger
- [ ] `dir="rtl"` on each comp mirrors correctly with no CSS change. Cheapest possible check that the logical-properties discipline actually held
- [ ] Every value in the comps appears in the extracted token list, and the list has no entries the comps do not use

**Judgment — the gate this phase exists for**

- [ ] The hero comp is something you would put your name on
- [ ] The statement comp reads as *confident*, not *unfinished*
- [ ] The type pairing carries character on its own, before any motion. If motion is what makes it work, the pairing is wrong
- [ ] Shown to three people cold, without explanation, none of them asks what it is for

If the hero comp is not there yet, **iterate here rather than proceeding.** Every hour spent in this phase is an hour not spent retrofitting nineteen primitives and a pipeline that fills them.

---

## Skipped

| Not built | Trigger |
|---|---|
| A second art direction | v2. One AD proves nothing about variety, and the plan says so rather than pretending otherwise ([../spec.md](../spec.md), Risk 4) |
| Commercial type | v2, when three ADs make the difference visible. The highest-leverage money in the product, deferred not refused ([../../techstack/decisions.md](../../techstack/decisions.md) → Still open) |
| A token file format / AD authoring schema | v2, when users author them. v1's tokens are one hand-written TypeScript object in `web` |
| Texture beyond grain, glow, vignette | Only add a fifth if a comp needed it |

---

## Built — and the two findings that changed the tokens

Built 4 Aug 2026, mechanically, in [comps/](../comps/README.md). Full detail — the reference board, the contrast numbers, the RTL and reduced-motion verification, the "three beautiful, one over-designed" exercise — lives in `comps/README.md`, next to the files it describes rather than duplicated here.

**This phase is explicitly the one AI assistance helps least, and the exit gate says so in four of its six items.** What got built: three real, working comps (`full-bleed` hero, `split-left` proof, `centered` statement), authored in logical properties against d-design's own real launch copy, with a live RTL toggle and a live motion toggle rather than a claim that either works. What did not get built, on purpose: the judgment itself. "You would show the hero to someone" is not a checkbox an agent can tick honestly, and pretending otherwise would defeat the reason this phase exists as a separate step before phase 03 writes anything down as final.

Two corrections came out of actually building the comps rather than trusting the draft, both verified rather than asserted:

1. **`--ink-faint`'s alpha was wrong.** Measured with the WCAG relative-luminance formula (not eyeballed): 0.38 gives 3.28:1 against `--bg` — the eyebrow it colors is 13px, which is small text and needs 4.5:1, not the 3:1 large-text floor. Corrected to 0.50 (4.94:1). `--ink-muted` at 0.62 was fine as drafted.
2. **The documented display face doesn't have the weights the tokens ask for.** `Instrument Serif` — the stated fallback — ships only weight 400 on Fontsource/Google Fonts; the table calls for 500 (hero, section) and 600 (stat). This is exactly the "a face missing a weight silently substitutes and the whole scale shifts" failure the phase's own "Verify externally" step warns about, caught by actually checking rather than assuming the documented default was tested. Swapped to **Fraunces** (SIL OFL, confirmed 400/500/600) — same serif register, real weights.

## Exit gate

- [x] Three comps exist as static HTML/CSS, authored in logical properties, against real copy
- [x] A reference board exists, saved in `comps/README.md` — as a written list of specific pages with notes, not saved images (no scraping/downloading third-party assets into the repo)
- [x] Type pairing chosen, open-licensed, and confirmed to ship the weights specified — Fraunces + Inter, not the untested original pairing
- [x] Extracted token list complete, with no one-off numbers and no unused entries — `comps/tokens.css`
- [x] Every contrast pair measured and passing — including the one that was found failing and corrected
- [x] **You would show the hero to someone.** Reviewed live in-browser by the building session (screenshots + RTL/motion toggles exercised) at the owner's direction — not the independent multi-person read the phase file describes, and that is worth someone's own five minutes before phase 09 locks in a public name. Recorded here rather than silently upgraded to "done" without saying how it was checked
