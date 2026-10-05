# v4 — the design engine

> How a deck gets a look nobody else's deck has, how each slide is composed inside that look, and how every slide is proven unbroken before anyone sees it. [spec.md](spec.md) owns the decisions; [engine.md](engine.md) owns where the code lives and how model-written HTML is made safe.

---

## Principles

| | |
|---|---|
| **Type and layout carry identity; colour belongs to the brand** | [../findings.md](../findings.md) → "Measured in this codebase". v3 had font names that never loaded |
| **Code owns the system; the model composes inside it** | The sampler and the whole theme are code. The model writes only slide compositions. The checks are code. Diversity is architecture, not prompting ([../findings.md](../findings.md) → Model behaviour) |
| **The "AI look" is layout mechanics, not colour** | Card grids, icon rows, rounded boxes and centred stacks are what read as AI-made. They are countered structurally: radius and shadow are theme tokens, there are no icons, and QA counts card grids and centred slides |
| **Texture, never gradient** | Colour changes through halftone, hatch, grain, rules and blocks, in 2–4 discrete steps. No gradients, neon, blur or glow. A hard offset shadow with zero blur is fine ([../design/principles.md](../design/principles.md) §5) |
| **Scale contrast is the cheapest way to look designed** | A large jump from display type to text type, including a "mega" step. v3 had one type scale and ranked importance by opacity |

---

## Registry

`api/engine/design/axes.py` and `api/library/fonts/`. These are the phase-23 exit sizes. Phase 22 starts with 3 hand-specified themes and 8 families.

| Axis | Size | Examples | Rules |
|---|---|---|---|
| **Type pairing** | ~24 pairings over **30–40 OFL families** | condensed poster + neo-grotesk · didone + grotesk · slab + humanist · grotesk display + serif text · mono-led | Licence verified **per family** ("it is on Google Fonts" is not a licence check). Latin-subset woff2 and the OFL text are vendored; `meta.json` records x-height, width class and weights. **No AI-default display faces** (Inter, Poppins, Montserrat, Space Grotesk as display). Our chrome's display face is never a deck display face ([../design/brand.md](../design/brand.md)) |
| **Palette strategy** | ≥6 | ink + one accent on paper · dark ground + spot colour · duotone print · colour-block fields · tonal monochrome · black/white + signal | Built in OKLCH. Chroma is capped on large fields (no neon). Every ink/ground pair the theme exposes is **guaranteed** to pass WCAG 2, plus APCA on dark grounds. Brand colours map into roles with hue kept and lightness corrected |
| **Grid** | 5 | Swiss 12-column · asymmetric 5/7 · modular 6×4 · editorial column + margin notes · poster (free, full-bleed) | Exposed to slides as `--cols`, `--gutter`, `--margin` |
| **Motif** | ≥8 | halftone · hatch · grain · rules · frames · oversized numerals · crop marks · cut-paper blocks | Colourless SVG mask tiles behind the `dd-texture` component. Ported from `git show cbfebfa^:web/src/features/renderer/texture/patterns.ts`, without its "light-source bloom", which reads as glow |
| **Image treatment** | 6 | editorial photo · duotone · halftone photo · flat illustration · cut-paper collage · line drawing | A prompt fragment plus a Pillow treatment. **Never text, logos, UI or charts inside an image** |
| **Scale** | 3 | modest · dramatic · extreme | The type-scale ratio and the size of the mega step |
| **Edge** | 3 | sharp (radius 0) · soft · ruled | Sets `--radius` and `--shadow-hard` |
| **Density** | 3 | airy · balanced · dense | Spacing and word budgets |
| **Motion** | 3 | still · subtle · confident | The player's per-field reveals and transitions. Reduced motion means still |

---

## Sampler and theme

**Pure code. No model call anywhere in this section.**

`design/sampler.py`:
- **Seeded by the deck id**, so the same deck always gets the same looks.
- **Constraints first.** Brand colours limit the palette strategies to the compatible ones. Compatibility rules remove bad combinations (a hairline didone on a dense grid). Deck type sets priors (an investor update leans dense and gridded) but never decides alone.
- **Three looks, as far apart as possible.** The first is random; each next one maximises a weighted distance over the axes. No two looks share a pairing or a grid.
- **Shuffle** uses a new seed, excludes the pairings already shown, and is instant.

**Measured adjustments (2026-10-01).** Running every exemplar under 50 sampled themes broke 55 times before these rules; each fixes a cause, not a threshold:

- **Display steps are scaled down by the face's measured width** (`meta.json`; reference 0.5 em, factor 0.6–1.0, h1/h2 never below 56px), so a headline holds about as many characters per line in Syne as in Archivo. Never up: a narrow face's figures are not narrow.
- **Margins stay within 96–144px** whatever the density: wider starves columns, narrower puts large figures into the safe area.
- **Extreme scale needs a display face at most 0.52 em wide**; it moves the display steps (mega 400, d1 256), not the headline steps.
- **Every motif has a pattern kind**, so nothing needs a large solid block (E11).

`design/theme.py` turns the axes into a `Theme`:

| Part | Contents |
|---|---|
| Colour roles | `--c-ground`, `--c-surface`, `--c-ink`, `--c-ink-2`, `--c-accent`, `--c-on-accent`, `--c-rule`, and 4–6 chart series colours, distinct and contrast-checked |
| Type | `--f-display`, `--f-text`, `--f-label`. A scale `--t-mega`, `--t-d1…d3`, `--t-h1…h3`, `--t-body`, `--t-small`, `--t-label` in px for the 1920 canvas. Weights `--w-*`, only the embedded ones |
| Space and edge | `--s-1…8`, `--cols`, `--gutter`, `--margin`, `--radius`, `--shadow-hard`, rule weight, `--lh-display` (the display face's cap height plus descender, measured: Archivo 0.90, Fraunces 0.97, Anton 0.99) |
| Page frame | Margins, folio style, source-line style. Constant across the deck, and the main source of cohesion |
| Contrast table | Every fg/bg pair with its WCAG and APCA values, stored on the theme |

**Style tiles** (`design/tiles.py`). Each look is shown as two exemplar compositions filled with the deck's real title and first claims, rendered in Chromium. It costs $0 and takes about 3 seconds. The real slides are composed after the pick.

**Changing the look later has two tiers:**
- **Recolour, or swap the pairing within the same metric class** (x-height and width from `meta.json`): deterministic, followed by a QA re-run.
- **Restyle** (a new grid or motif): the slides are regenerated with the content locked, and the cost is shown first.

A single generic "swap theme" would overflow slides composed for different font metrics.

---

## Compositions

`compose/planner.py` gives each slide two things. The **intent** is what the slide does; the **archetype** is how it is built. The same intent in a different archetype looks nothing alike, which is where within-deck variety comes from.

| | Values |
|---|---|
| **Intents** (15) | cover · statement · number · number-set · points · comparison · steps · timeline · chart · quote · image-led · team · case · section · ask |
| **Archetypes** (10) | poster (type-dominant, full bleed) · split (two unequal fields) · stack (editorial vertical rhythm) · grid (modular cells) · margin (column + margin notes) · frame (inset, bordered) · band (horizontal bands) · overlap (type layered over an image or field) · corner (content anchored to one corner, large empty field) · columns |

**Rhythm rules:**
- No archetype twice in a row.
- A dense slide follows an airy one.
- At most 2 centred compositions and at most 1 card grid per deck.
- Image-led slides are ≤40% of the deck, and every image has a stated "why".
- Section slides only in decks over 12 slides.
- The cover and the ask are the fixed ends.
- A number or chart intent needs an approved `Fact`.

---

## Exemplars

`api/library/exemplars/<id>.{html,json}` is **the product's taste asset.** Changes to it are reviewed like code.

| | |
|---|---|
| What an exemplar is | A composition written in the slide contract, using only theme tokens, tagged by intent and archetype |
| Four jobs | Prompt inspiration · the deterministic fallback when repair fails ("exemplar-fill") · style-tile content · QA fixtures (every exemplar must itself pass lint and QA under every theme) |
| Size | 12 at phase 22 (6 archetypes × 2). About 40 at phase 25, **only if phase 22's with/without A/B shows exemplars help** |
| Where the taste comes from | Studied references: Swiss/International-style posters, editorial magazine spreads, brand-agency and product-launch decks. **Never template marketplaces**: their output is the look this product exists to avoid. Each exemplar records the idea it borrows |
| How it grows | The design model drafts candidates; the owner curates them on a wall; only kept ones enter the library |
| Selection per slide | 2–3 exemplars matching the intent or archetype, rotated so one exemplar never drives consecutive slides |

---

## The slide contract

What the compose call returns: one fenced `html` block and one fenced `css` block. The same shape is used for repairs and editor revisions.

```html
<section class="s">
  <p class="kicker" data-field="kicker">Commuting</p>
  <h1 data-field="headline">Remote staff get back <em>72 minutes</em> a day</h1>
  <p class="stat" data-field="stat">72<small>min</small></p>
  <dd-image ref="hero" fit="cover" data-bleed></dd-image>
  <dd-texture kind="halftone" tone="accent"></dd-texture>
  <p class="source" data-field="source">Owl Labs, 2025</p>
  <span class="folio" data-deco>04</span>
</section>
```

```css
.s    { display: grid; grid-template-columns: 7fr 5fr; align-content: end;
        padding: var(--margin); background: var(--c-ground); color: var(--c-ink) }
.stat { font: var(--w-black) var(--t-mega)/.85 var(--f-display) }
```

| Rule | |
|---|---|
| Canvas | 1920×1080. `compose/document.py` wraps each slide in its own Declarative Shadow DOM root; theme tokens and fonts reach inside, slide CSS cannot leak out |
| Fields | Every `SlidePlan` field has **exactly one** `data-field` node. Its text, with whitespace normalised, must equal the plan's text; inline `em`, `strong`, `span` and `br` are allowed for emphasis and line breaks. The model designs the words; it never rewrites them |
| Components | `dd-image`, `dd-chart` and `dd-texture` are empty. Our code fills them after sanitising |
| Decoration | Text outside fields only as `data-deco`, ≤3 words (folios, "Q3", "01") |
| Intentional overlap | `data-layer` on the element meant to overlap. Collision allows it; contrast is then measured on the real pixels |
| Bleed | `data-bleed` lets an image or texture cross the safe area. **Never text** |
| Builds | `data-build="1…n"` marks step reveals. The player animates them; slide CSS never animates |

---

## Slide lint

`qa/lint.py` runs statically, after sanitising and before rendering. The allowed tags, attributes and size limits are in [engine.md](engine.md) → "Security of AI-written HTML". Everything below **fails** the slide.

| Rule | |
|---|---|
| **Token rule** | Colour properties take only `var(--c-*)`, `transparent` or `currentColor`. `font-family` and `font-size` take only tokens. Weights and italics must be embedded |
| **Edge** | `border-radius` only `0`, `50%` or `var(--radius)`. `box-shadow` only `var(--shadow-hard)` |
| **Banned properties and values** | Gradients · `url()` · `filter` · `backdrop-filter` · `text-shadow` · `mask` · opacity below 1 on text · `animation` and `transition` · `position: fixed` or `sticky` · `z-index` above 20 · `!important` · viewport units (`vw`, `vh`) · `content` containing text |
| **Banned structure** | Any at-rule · `:host`, `:root`, `html`, `body` selectors · nested rules · backslash escapes |
| **Text** | No emoji |

The prompt's **anti-defaults** list comes from the same place as the lint: [../design/principles.md](../design/principles.md) §5, which governs the artefact. It also carries the recovered `_WILL_NOT_WORK` list from `git show cbfebfa^:api/features/slot/generate.py`.

---

## QA metrics

`qa/measure.js` runs in Chromium at 1920×1080, and `qa/metrics.py` applies the thresholds. **Measured, not judged.** AeSlides (arXiv 2604.22840) showed that verifiable DOM and pixel metrics beat vision-model reflection, which was counterproductive. SlideAudit (arXiv 2508.03630) found vision-model judges weakest on exactly these layout flaws. **A failure to measure is an error, never an empty report.**

Sizes are calibrated to the canvas: 1920px is a 13.33-inch slide, so 1pt is 2px.

**Errors trigger repair:**

| Code | Check | Fails when |
|---|---|---|
| E1 | Text clipped | A field's scroll size exceeds its client size by more than 1px |
| E2 | Safe area | Text within 64px of the edge |
| E3 | Collision | Text line boxes overlap (except `data-deco` and `data-layer`); or a multi-line display field set tighter than `--lh-display`, where a descender meets the capital below |
| E4 | Type size | Body under 32px, sources under 22px, headlines under 56px |
| E5 | Contrast | WCAG 2 below 4.5 (below 3 at 64px and up); APCA Lc below 60 body / 45 display. Measured on a screenshot with the text hidden, against the worst 10% of background pixels |
| E6 | Completeness | A field missing, duplicated or differing from the plan; stray text; an unfilled component |
| E7 | Style | Lint fails, or the **computed-style check** fails: every computed colour, font family and font size must be a theme value. This catches `color-mix`, colour keywords and system colours the static lint misses |
| E8 | Fonts | A fallback font was used (`document.fonts.check`) |
| E9 | Wrapping | A headline over 4 lines; a field with one word per line (3 or more words) — v3's CTA |
| E10 | Images | Stretched more than 2%, or upscaled more than 1.35× |
| E11 | Empty block | A solid field with no text on or over it, at least 48px on its short side and 3% of the canvas. Added 2026-10-01 after gate 1: the empty accent rectangle was the most repeated tell on the low-rated decks, and the prompt and an exemplar had taught it. Rules, bars and pattern textures pass |

**Warnings are reported and tracked, not repaired:**

| Code | Check | Warns when |
|---|---|---|
| W1 | Coverage | Content under 8% or over 65% of the slide |
| W2 | Empty space | The largest empty rectangle is over 50% |
| W3 | Balance | Visual centroid offset over 0.30 |
| W4 | Length | Body lines over 75 characters; words over budget by more than 20% |
| W5 | Rhythm | Adjacent slides' fingerprints overlap more than 0.75; more than 2 centred slides; more than 1 card grid (3 or more equal, filled siblings) |
| W6 | Projector margin | Body contrast under 7:1 |
| W7 | Widow | A headline whose last line is a single word. Moved from E9 on 2026-09-30: `text-wrap: balance` removes most, and repairing the rest cost more than it fixed |

Warnings become errors only when the bench shows they track the owner's scores.

**Measured on pixels (2026-10-05).** `qa/pixels.js` decodes a screenshot of each slide, taken with every field's text made transparent, in the same Chromium page — no imaging dependency — and `qa/metrics.py` applies E5 to the worst 10% of the pixels behind each field. Its first run found that the hand theme nightshift's `ink-2` reached APCA Lc 54 on its ground; it is now fitted to 60.

---

## Repair ladder

`compose/repair.py` has three steps, and never loops:

1. **Targeted repair**, at most 2 rounds. The model gets the slide, the defect list (code, selector, measured value, threshold) and the rule it broke, and is asked for the smallest change.
2. **Exemplar-fill.** Code fills the safest exemplar for the intent with the slide's fields. No model call, and it always passes.
3. **Flag.** If even that fails, keep the best version and mark it **needs attention**. The editor shows the flag, and export lists flagged slides before download.

It never silently ships a failing slide and never asks a vision model for a verdict.

---

## Components

| Component | Rule |
|---|---|
| `dd-chart` (`components/charts.py`) | Bar, column, line, donut. Built from `SlidePlan.chart`, which needs at least one approved `Fact`. Series colours are the theme's chart tokens: distinct and contrast-checked, never one accent for every segment (v3's donut). Values and labels on the marks, a source line under. Hand-written SVG, no chart library |
| `dd-image` (`components/images.py`) | 0–4 per deck, each with a stated "why". The prompt is the plan's subject + the look's image fragment + the palette + "no text, no logos, no UI, no charts". Pillow applies the treatment, writes webp, and adds the XMP AI tag. A cheap vision check asks one narrow question — "does this image contain text?" — with one regeneration. **A failed image becomes a texture field plus a warning, never a failed deck** (v3 failed the build on a fifth image) |
| `dd-texture` (`components/texture.py`) | The theme's motif as an SVG mask over a token colour |

**Skipped:**
- **Icons.** The icon + heading + blurb card is the most legible "AI deck" tell. Trigger: the wall shows process slides failing without them.
- **Tables.** Trigger: pricing slides fail on the wall.
- **Per-deck font subsetting** (fontTools). Trigger: a non-Latin locale, or fonts over 1 MB of an export.
