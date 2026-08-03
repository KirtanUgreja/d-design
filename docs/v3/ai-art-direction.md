# AI-Derived Art Direction

Drop in a reference. Get a complete art direction. The single biggest demo moment in the product.

## It is not a new system

v2 gave users four control axes. Derivation is **the AI filling in those same four controls**, then running the same linter, producing the same `ArtDirection` record.

```
reference ──▶ { density, contrast, typeCharacter, motionEnergy } ──▶ ArtDirection ──▶ linter
                        the v2 control axes
```

Nothing downstream knows a derived AD from a hand-authored one. `source: 'derived'` exists for provenance and for the reference thumbnail in the UI — not for behavior.

If derivation needs a fifth axis to express a reference, that axis was missing from v2's controls too. Add it to both.

## Inputs

| | Handling |
|---|---|
| **Screenshot / image** | Vision model reads the four qualities. Most flexible, best demo |
| **URL** | Server captures a screenshot, then the image path. Most requested, most abuse-prone |
| **Moodboard (3–5 images)** | Qualities extracted per image, then synthesized. Genuinely better output — it's how designers actually work |
| **Plain description** | "Warm, editorial, 1970s Swiss poster." No vision needed. Cheapest path to a working version — **build this first** |

Description-first is deliberate. It exercises the whole derivation → linter → render path without a vision model in the loop, so when images arrive you are debugging perception rather than plumbing.

### Vision mechanics — give it tools, not more thinking

Opus 5 sits in the high-resolution vision tier: **2576 pixels on the long edge**, up to ~4784 visual tokens per image, with coordinates mapping 1:1 to actual pixels (no scale-factor math). It is meaningfully stronger on document, chart, and diagram understanding and on UI/frontend visual replication than prior models.

The non-obvious part, and the one that shapes this feature's architecture:

> **Giving the model tools to iteratively analyze, crop, and visually verify its own work is a markedly more cost-effective lever than raising thinking effort.**

For AD derivation that means the pipeline should not be *one big image plus `effort: "max"`*. It should be: hand the model a crop tool and let it inspect the reference the way a designer would — zoom the type to judge character, sample a region to read density, isolate a component to assess spatial rhythm. Each of those is a cheap targeted look rather than one expensive global stare.

**Cost is not the constraint here either.** At ~4784 tokens per image and $5/MTok input, a five-image moodboard is roughly $0.12 of vision. Consistent with [../v1/ai-pipeline.md](../v1/ai-pipeline.md): the expensive thing about this product is never the tokens.

One migration note: prompt-side workarounds written for older models' vision limitations are worth re-validating rather than carrying forward — several are now counterproductive on current models.

## What is extracted, and what is refused

**Extracted — abstract qualities:**

- density and spatial rhythm
- contrast and mood
- type *character*: serif / geometric / grotesque, restrained / aggressive, scale aggression
- motion energy

**Never extracted:**

- the reference's fonts
- its exact colors
- its literal layouts or components

Two reasons, and the second is the one that matters. A tool that reproduces a reference site's design is a plagiarism machine with your name on it. And quality-derived output is simply *better*: an art direction in the spirit of the reference, adapted to the user's own brand kit, beats a degraded copy of someone else's page — which would clash with their brand anyway.

Colors come from the user's brand kit, mapped through the derived AD's `brandMapping`. Fonts come from their brand kit or the system's curated set, chosen to match the derived *character*. The reference supplies feel, never assets.

**This is testable, so test it:** feed a well-known site, assert the output shares none of its fonts and no color within ΔE 10.

## Priors — where the quality actually comes from

A vision model can report "dark, dense, aggressive type, fast motion." Turning that into a *good* art direction requires knowing what those qualities look like when done well.

That knowledge is the 3 hand-authored ADs. Derivation interpolates and extrapolates from them rather than generating tokens from nothing:

- `cinematic-dark` anchors dark / atmospheric / slow
- `editorial-light` anchors light / restrained / serif
- `bold-brutalist` anchors hard / dense / aggressive

A reference reading as "dark but snappy and geometric" resolves near `cinematic-dark`'s color, `bold-brutalist`'s type aggression, and `mechanical-snap` motion — every component of the result already proven to work.

**This is the real work of the feature, and the main risk.** Three anchors is thin. Expect to hand-author two or three more purely as derivation priors, and expect that — not the vision model — to be what makes output good.

## Validation

Derived ADs run the v2 linter unchanged. Hard failures: contrast, scale monotonicity, scale range, line height, measure, spacing ratios, motion bounds, reduced-motion presence, budget sanity.

Failure → one repair attempt with the specific violations as context, exactly like scene repair. Second failure → surface honestly. Do not ship a broken AD, and do not silently fall back to `cinematic-dark` — a user who dropped in a moodboard and got the default deserves to be told why.

## What the linter cannot catch

It enforces readability. It has no opinion on beauty.

A derived AD can pass every rule and still be ugly, generic, or wrong for the brand. Mitigations, in order of value:

1. **Good priors** — the anchor ADs above. This is 80% of it
2. **Show three candidates, not one** — reuse v2's compare view; users pick with their eyes
3. **Full editability** — a derived AD lands in the v2 control panel, adjustable on all four axes
4. **Never auto-apply** — derivation proposes, the user disposes

Point 2 is worth more than it looks. One result invites judgment of the system; three invite a choice, and a choice is a much better experience even when one candidate is weak.

## Abuse

URL input will be used to clone competitors. The abstract-qualities constraint is the structural answer — the output genuinely cannot reproduce the reference — but state it plainly in the UI when a URL is pasted: *"We'll capture the feel of this page, not its design."*

Set expectations at the input, not in a support ticket after someone expected a pixel copy.
