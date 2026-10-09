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
| **Type pairing** | ~24 pairings over **30–40 OFL families** | condensed poster + neo-grotesk · didone + grotesk · slab + humanist · grotesk display + serif text · mono-led | Licence verified **per family** ("it is on Google Fonts" is not a licence check). Latin-subset woff2 and the OFL text are vendored; `meta.json` records x-height, width class and weights. **11 display families are variable** (phase 36): one file per family, and each deck draws its own instance — weight within ±100 of the pairing's, width where the face has it, Fraunces' softness and wonk — never more than 5% wider than the tested weight; optical size follows the type size. Families stay finite (typefaces are drawn by people); the instance is continuous. **No AI-default display faces** (Inter, Poppins, Montserrat, Space Grotesk as display). Our chrome's display face is never a deck display face ([../design/brand.md](../design/brand.md)) |
| **Palette** | continuous | No named strategies (phase 36): ground lightness and tint, ink tint, the accent's hue split, lightness and chroma are all drawn per deck (`palettes.generate`); a tone only leans the draw (`TILTS`) | Built in OKLCH. Chroma is capped on grounds (0.035) and on light accents on dark grounds (no neon). Every ink/ground pair the theme exposes is **guaranteed** to pass WCAG 2, plus APCA on dark grounds. Brand colours map into roles with hue kept and lightness corrected |
| **Grid** | 5 | Swiss 12-column · asymmetric 5/7 · modular 6×4 · editorial column + margin notes · poster (free, full-bleed) | Exposed to slides as `--cols`, `--gutter`, `--margin` |
| **Motif** | a grammar | Generated per deck (`patterns.motif`, phase 36): an element — dot, dash, ring, cross, square, bar — sometimes with a second layered between, on a lattice whose pitch, stagger, rotation, element size and stroke are continuous. Used as `<dd-texture kind="motif">`. The older fixed kinds (halftone, hatch, grid…) stay, with generated geometry | Colourless SVG masks over a token colour; one slide-sized mask, so it rotates seamlessly and never visibly repeats |
| **Image treatment** | 6 | editorial photo · duotone · halftone photo · flat illustration · cut-paper collage · line drawing | A prompt fragment plus a Pillow treatment. **Never text, logos, UI or charts inside an image** |
| **Scale** | 3 | modest · dramatic · extreme | The type-scale ratio and the size of the mega step |
| **Edge** | 3 | sharp (radius 0) · soft · ruled | Sets `--radius` and `--shadow-hard` |
| **Density** | 3 | airy · balanced · dense | Spacing and word budgets |
| **Motion** | 3 | still · subtle · confident | The player's per-field reveals and transitions. Reduced motion means still |

---

## Generated, not picked

**Pure code. No model call anywhere in this section.** *Decided 2026-10-05 by the owner:* the user is never asked to pick a style. A choice among three looks is a template gallery with fewer templates, and it is the move that makes a tool feel like Gamma.

The model is the one generative identities follow (MIT Media Lab's 2011 identity, and the dynamic-identity work since): a designer writes the **rules**, the algorithm draws a unique instance each time, and the instance can respond to its content.

`design/sampler.py` → `look_for(deck_id, deck_type, tone, words, brand_hex, nonce)`:
- **One look per deck.** Seeded by the deck, its words and a `nonce`; *Try another look* in the editor is a new nonce.
- **Discrete only where it must be:** a font pairing (fonts are files) and a grid arrangement. Colour, texture and the display face's instance are continuous.
- **Continuous everywhere else:** hue anywhere on the wheel (steered by topic words 70% of the time — climate leans green, finance blue), two type-scale ratios, margin, gutter, rule weight, radius, display tracking, and the texture geometry (`design/patterns.py`: dot pitch and size, hatch angle and spacing, grid pitch, line weight).
- **The deck's mark:** an emblem drawn from its own title (rings, bars or a dotted arc), used on the cover and the ask. No other deck has it.
- **Tone sets the drama:** plain decks get modest scale ratios and quiet palettes; bold decks steeper ratios and darker grounds.
- **Constraints first, as before:** a brand colour fixes the accent hue and turns off the two-colour split; compatibility rules remove bad combinations; deck type sets priors.
- **Measured:** 300 decks give 300 distinct looks; contrast holds over 1,000 seeds; every exemplar passes QA under 50 generated looks (`tests/test_design.py`).

`sample()` still returns three far-apart looks, for the internal tile wall only.

**Next: [plan/36-independent-design.md](plan/36-independent-design.md)** removes the remaining finite parts — the exemplars in the prompt, the archetype names, the palette strategies and motif kinds — in favour of per-slide composition targets, a novelty archive and variable fonts.

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

**Style tiles** (`design/tiles.py`) are now an internal tool for the bench wall: three looks, two compositions each, $0. Users never see them.

**Changing the look later has two tiers:**
- **Recolour, or swap the pairing within the same metric class** (x-height and width from `meta.json`): deterministic, followed by a QA re-run.
- **Restyle** (a new grid or motif): the slides are regenerated with the content locked, and the cost is shown first.

A single generic "swap theme" would overflow slides composed for different font metrics.

---

## The studio (2026-10-09) — replaces compositions, references and exemplars

**Decided by the owner on 2026-10-09** after two live decks: "delete the whole build agent and rebuild it in layers". The reference library, the composition targets, the novelty archive and the exemplars are deleted (`git log` keeps them; tag `v3-final` and the phase-39 commits). The engine is now `api/engine/studio/`, four layers, each on Sonnet 5.5:

| Layer | File | Job |
|---|---|---|
| 1. Research | `research.py` | Two web searches in parallel. The **product file** covers what it is, what it does, for whom, features, pricing, team, traction and competitors. The **market evidence** covers what the arc needs. A line or number is kept only if a returned page quotes it |
| 2. Outline | `outline.py` | The argument. Each slide has a headline claim, a body line (at most 28 words) that explains it to a reader alone, points, a figure, a chart from approved facts, or a drawn visual. Every number is linked to a fact |
| 3a. Art director | `direct.py` | One call that sees the whole outline and the design system. It plans each slide's **hero** (headline, number, chart, visual, image, diagram, quote or list), **field** (ground, surface, accent or ink), whether it gets a picture (at most 3 per deck) and a buildable **idea** (placement, scale, crop, bleed). Rules: no two neighbours share a layout, hero or field, and the cover and ask are the strongest slides. If the call fails, a plain plan that still varies by position is used |
| 3b. Designer | `design.py` | Writes one slide in HTML, CSS and **flat SVG** from the plan, inside the contract (`slide.py`). There is no template: the plan and the deck's design system are the only inputs |
| 4. Improver | `improve.py` | A creative director gets a **screenshot of the rendered slide** (a 1280px JPEG) and its code. It critiques the slide in up to five lines (hierarchy, scale, canvas, alignment, boldness, sameness) and returns a redesign. The redesign is kept only if QA measures it no worse |
| 5. Deck review | `review.py` | One call sees **every slide on one labelled sheet** and judges the deck as a whole: rhythm, slides that look alike, slides that break the style, and the AI tells. It sends back at most two slides with one note each, and the improver redoes them. A redo is kept only if QA measures it no worse. Slides that already carry the logo or a picture are left alone |

**What the research of 2026-10-09 changed.** Sources: Gamma 5's launch (October 2026) and designers' teardowns of AI slides; full list in the commit.
- **The AI tells**, a list in `slide.py` that the art director, designer and critic all check: three equal boxes, metric tiles, a coloured bar beside every block, every slide the same weight and structure, everything centred, an italic serif flourish on a cream ground, icons standing in for ideas.
- **Rhythm:** a bold opener, a denser middle and an open close; one idea per slide, and at most one number as the hero. The art director now thinks at medium effort.
- **Pictures are flat editorial illustrations** in the deck's accent, not AI photographs, which give themselves away through hands, light and implausible detail. Gamma 5 moved to illustration for the same reason.
- **A deck-level look** (layer 5): a slide is judged against its neighbours, which a per-slide critic cannot see.

**What open-design taught us (2026-10-09).** Studied: [nexu-io/open-design](https://github.com/nexu-io/open-design), specifically its deck template's checklist (guizang-ppt) and its critique skill (after huashu-design).
- **Rhythm is enforced by code** (`direct.rhythm`): never three slides in a row on the same field, and at least one dark and one light slide in any deck of five or more. Big-number slides and dense slides alternate (prompt).
- **The critic scores five dimensions** (consistency, hierarchy, detail, readability, innovation), each 0–10 with one line of evidence. The score is the worst sustained band, and inflated scores are called out. The deck review sends its five scores on a `review` event.
- **One more tell:** a kicker that says the headline again in other words.
- Not taken: their **five-direction picker**. Users never pick a look from a menu (owner, 2026-10-05). Also not taken: WebGL backgrounds and CDN icon fonts, which break the offline export and the no-icons rule.

**Flat SVG (new).** The designer may draw with `svg g path rect circle ellipse line polyline polygon`, using geometry attributes only. The sanitizer keeps nothing else: no text, links, scripts, `foreignObject`, styles or gradients. Colour is applied through CSS classes, which the lint restricts to `var(--c-…)`. An unstyled shape defaults to `--c-ink`, never browser black.

**What stayed:** the theme tokens and visual languages (type, palette, texture policy), the sanitizer and lint at entry, Chromium QA on every slide, components drawn by code (`dd-chart`, `dd-visual`, `dd-image`), the logo placed by code, the budget cap that fails closed, resume without paying twice, and abort.

**Cost (estimate, unmeasured until the first live deck):** about $1 a deck, against $0.3 before. The art director costs about $0.05, then a design call and an improver call per slide, each with the deck's contract cached.

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
| Components | `dd-image`, `dd-chart`, `dd-visual` and `dd-texture` are empty. Our code fills them after sanitising |
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
| E12 | Logo | The user's logo (placed by code, phase 38) outside the safe area, under 32px tall, or with text over it. The pipeline then takes it off the slide and warns W9 |

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
| W8 | Near-repeat | A composition within ε of an archived slide or another slide in the deck after its one steered retry (phase 36) |
| W9 | Logo left off | No empty safe-area corner for the logo, or placing it broke the slide |

Warnings become errors only when the bench shows they track the owner's scores.

**Measured on pixels (2026-10-05).** `qa/pixels.js` decodes a screenshot of each slide, taken with every field's text made transparent, in the same Chromium page — no imaging dependency — and `qa/metrics.py` applies E5 to the worst 10% of the pixels behind each field. Its first run found that the hand theme nightshift's `ink-2` reached APCA Lc 54 on its ground; it is now fitted to 60.

---

**Shapes per deck (2026-10-09).** A visual language's signature shape is used on at most 3 slides in a deck. After that, the compose call is told to leave the reference's `dd-shape` out. A live Bauhaus deck had the same circle on 8 of its 10 slides.

**Brand colour (2026-10-09).** At the outline gate the user can give one colour. The palette is built around it: its hue is kept, and its lightness is fitted for contrast. The logo's main colour is offered as a suggestion, never applied on its own. **New colours** keeps the brand accent and changes the ground and ink.

## Repair ladder

The safety net under the studio (`studio/build.py`) has three steps and never loops:

1. **Targeted repair**, at most 2 rounds. The model gets the slide, the defect list (code, selector, measured value, threshold) and the rule it broke, and is asked for the smallest change.
2. **The code-built layout** (`studio/design.py` → `fallback`). Code builds the slide from its fields: a colour field for a number, a ruled list, a chart or visual below the claim, or a single sentence at poster scale. No model call; words fit by construction. It is also the style preview and "Fit to slide".
3. **Flag.** If even that fails, keep the best version and mark it **needs attention**. The editor shows the flag, and export lists flagged slides before download.

The improver (layer 4) looks at a screenshot to judge **design**. Whether a slide is **broken** is still decided only by measurement.

---

## Components

| Component | Rule |
|---|---|
| `dd-chart` (`components/charts.py`) | **Form by the data's job** (phase 37, `charts.form`): bar (long names, sorted), column, line (time), area (one long trend), stacked (parts of a whole; replaces the donut), dumbbell (before and after), slope (two moments, many items), diverging (above or below zero), waffle (a share of 100). Built from `SlidePlan.chart`, every value an approved `Fact`. Colour last: the deck's series (`design/dataviz.py`) pass the dataviz checks — lightness band, chroma floor, colour-blind ΔE ≥ 8 and normal-vision ΔE ≥ 15 on adjacent pairs, 3:1 on the ground — in a fixed order, never cycled. One highlight in slot 1, the rest a quiet tint; values on the data; a legend only for two or more series; one callout computed from the values ("3.8x since 2022"). The data rides as `<desc>` text and in the speaker notes. Hand-written SVG, no chart library |
| `dd-visual` (`components/visuals.py`) | **A picture of the product's world, drawn by code** (owner, 2026-10-09: "don't limit it to simple shapes"). Five kinds: a voice waveform, an app on a phone, a web app in a browser, a chat, and a flow of steps. The storyline picks a kind for at most three slides that show the product, never a chart slide. It also writes up to four lines (at most 6 words each, no numbers) that become the screen's rows, the chat's messages or the flow's steps. Flat fills in theme roles only, so a brand colour carries through. A slide with a visual takes no generated image. Its words sit inside the component, so QA skips them like a chart's labels |
| `dd-image` (`components/images.py`) | 0–4 per deck, each with a stated "why". The prompt is the plan's subject + the look's image fragment + the palette + "no text, no logos, no UI, no charts". Pillow applies the treatment, writes webp, and adds the XMP AI tag. A cheap vision check asks one narrow question — "does this image contain text?" — with one regeneration. **A failed image becomes a texture field plus a warning, never a failed deck** (v3 failed the build on a fifth image) |
| `dd-texture` (`components/texture.py`) | The theme's motif as an SVG mask over a token colour |

**Skipped:**
- **Icons.** The icon + heading + blurb card is the most legible "AI deck" tell. Trigger: the wall shows process slides failing without them.
- **Tables.** Trigger: pricing slides fail on the wall.
- **Per-deck font subsetting** (fontTools). Trigger: a non-Latin locale, or fonts over 1 MB of an export.
