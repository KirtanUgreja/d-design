# Phase 39 — design reset: languages, references, images

> This phase makes true that a deck looks designed by a person *and* unlike other decks. Each deck gets a **visual language** (a coherent system a studio would recognise), each slide is **adapted from a strong reference** in that language rather than invented from nothing, **imagery** in one style carries most of the visual weight, and the user **sees the style before the build**.

**Depends on:** 36, 37 · **Replaces:** the 2026-10-08 art-direction experiment (`design/direction.py`, free `dd-shape` use) · **Size:** L · **Owner, 2026-10-08:** "very bad, messy… update our whole system"; the reference library is "absolutely fine" · **Evidence:** [../research-2026-10.md](../research-2026-10.md) · **Schedule:** [master-plan.md](master-plan.md) (build 2026-10-09, test 2026-10-10)

## Why

Both walls of 2026-10-08 failed for one reason: the model designed every slide from nothing. Without a reference it fell back to its favourite editorial habit (one house style). With free shapes and no reference it made noise. Every strong system works the same way: a coherent design system per deck, **real references adapted to the content**, imagery, and selection with measured checks. Examples are PPTAgent, SlideCoder and DeepSlides in the literature, and Gamma 5, Pitch and Gemini in the market.

## Make

### 1. Visual languages (B1)

A language is a whole system, not a palette: grid, type behaviour, how images sit, how numbers and lists look, what it never does. Each lives in `api/library/languages/<id>.json`, authored by hand, never generated. It holds:
- the `brief` the compose prompt reads;
- the pairing kinds it allows;
- its grounds, radius and texture policy;
- whether it uses `dd-shape`;
- its **image appetite** (the share of slides with an image) and **image styles**.

| id | Name | The system | Type | Images | Never |
|---|---|---|---|---|---|
| `swiss` | Swiss grid | Strict 12-column grid, flush left, heavy rules as structure, numbers huge | grotesk, wide | ~20%, square-cropped on the grid; monochrome detail photography | centring, rounded corners, decoration |
| `editorial` | Magazine editorial | Serif display, pull-quote moments, text in columns, images half- or full-bleed with captions | serif, didone | ~40%; editorial documentary photography | thick rules, shapes |
| `poster` | Type poster | Type is the image: giant condensed words cropped by the edge, colour-block halves, few words | condensed, wide | ~15%; high-contrast graphic photography | small type as the main element |
| `cinematic` | Cinematic | Full-bleed imagery; type on a solid band or dark ground; very few words | serif, didone, grotesk | ~70%; cinematic photography, natural light | light grounds, lists of more than 3 |
| `journal` | Data journal | A tag bar, the headline as a claim, the chart or the figure dominant, annotations, source lines | serif, slab, grotesk | ~15%; documentary, muted | decoration, more than one accent |
| `minimal` | Quiet minimal | One statement in a vast field, a single object image, light hierarchy, one number | grotesk, wide | ~40%; studio object photography or soft 3D on a plain ground | more than two blocks, rules |
| `bauhaus` | Geometric modern | One or two large geometric shapes as structure (a half-circle framing a number, a quarter in a corner), strong colour fields | grotesk, wide | ~25%; abstract flat geometric illustration | more than two shapes, scattered shapes |
| `humanist` | Warm humanist | Soft radius, warm surfaces holding the content, friendly scale, illustration | serif-display (Fraunces soft), slab, grotesk | ~40%; warm flat illustration | hard rules, dark grounds |

**The sampler draws the language first.** It balances by how often each language has been used (the archive), with a light prior from tone and deck type. It then draws tokens only within what that language allows; the colour, font instance and texture geometry remain continuous per deck, as in phase 36.

### 2. The reference library (B2)

`api/library/references/<language>/<shape>-<n>.{html,css,json}`, in the slide contract, tokens only.

**Shapes.** There are 8, each covering one or more planner intents:

| Shape | Intents |
|---|---|
| `cover` | cover |
| `statement` | statement, question, section, quote, image-led |
| `number` | number |
| `points` | points, team, case |
| `comparison` | comparison |
| `sequence` | steps, timeline |
| `chart` | chart |
| `ask` | ask |

**Size.** 8 languages × 8 shapes = **64** references; cut line 48, floor 40. One reference per shape and language, plus a second for `statement` and `points` where time allows.

**Metadata** (`<id>.json`):
- `id`, `language`, `shape`;
- `fields`: the most it holds, e.g. `kicker`, `headline`, `point-1..3`, `stat`, `stat-label`, `source`;
- `image`: `none`, `half`, `full`, `inset` or `background`;
- `variants`: the changes it allows, e.g. `mirror`, `image-other-side`, `hero-number`, `dark-field`;
- `idea`: the design idea it borrows, in one line.

**Images.** A slot is `<dd-image class="…" aspect="3:2|2:3|1:1|16:9">`. Text over an image always sits on a solid field. Opacity is banned, so a scrim is a field.

**Authoring rules:**
- Every field the shape can hold appears in an element with `data-field`.
- An absent field can be removed without breaking the layout.
- No sample words are ever shown: the filled reference is QA's input.

**QA.** Each reference, filled with long and with short words, passes QA under 30 sampled looks of its language. This is a test.

**`cli refs --wall`** renders every reference under two looks with real words, so the owner can curate it. Kept references are listed in `library/references/kept.json`; a dropped one is never retrieved.

### 3. Retrieval and reference-fill (B3)

`compose/references.py`:
- `shape_of(plan)` maps the plan to a shape.
- `pick(language, shape, …)` returns a reference and an alternate. It never reuses a reference within a deck. Across decks it takes the least-used (usage counts kept in the store), and a reference with an image slot only when the deck's image budget allows.
- `fill(ref, fields)` is the no-model fallback. It replaces the old exemplar-fill: it places the words and removes absent fields. It is design-quality, because every reference passed QA.

### 4. The compose prompt, `compose.v11` (B4)

**The prefix,** cached per deck:
- the contract and the legibility rules (as v10);
- the theme tokens;
- **the language's brief**, plus `dd-shape` only if the language uses shapes.

**The user part,** per slide:
- the fields;
- **the reference** (HTML and CSS), and the alternate;
- one **variation** chosen by code from the reference's `variants`, never the same twice in a row.

The instruction: *adapt this reference to these words and tokens; keep its system (grid, how type behaves, how elements relate); change proportions only to fit the words; never copy its sample words.*

**Removed:**
- the geometric target text;
- the ideas block;
- the house-style lines;
- the art-direction model call;
- free shapes.

**The ladder:**
1. compose;
2. 2 targeted repairs;
3. a fresh compose with the **alternate** reference;
4. **reference-fill**;
5. the code layout;
6. the flag.

**The novelty gate** retries only within a deck. Across decks, reference rotation and the measured archive do the job: retrying a reference's own geometry would only waste money.

### 5. Imagery (B5)

**Model call.** `Seam.complete_image(prompt, model, aspect)` uses OpenRouter's chat completions with image output and returns PNG or JPEG bytes. The budget guard and the ledger apply.

**`components/images.py`:**
- **The prompt:** the slide's subject from its headline and points, the deck's image style and its accent hue as a mood. It always ends: *no text, no letters, no logos, no UI, no charts*.
- **`treat()`:** Pillow decodes, crops to the slot's aspect, resizes to at most 1600 px, writes webp at quality 82 and strips metadata.
- **`fill()`:** puts it into `dd-image` as a data URI after sanitizing, as charts do.

**The budget.** The language's appetite × the slide count, capped at 6 a deck; the cover first if its reference has a slot.

**Concurrency.** Images are generated **while** the slide is composed, never before or after it.

**Failure.** A failed or refused image leaves a quiet `--c-surface` field with the deck's texture. It is never a broken box and never a failed deck.

**Export.** Images are embedded: the deck stays one offline file. The median export must stay ≤ 6 MB.

**Model.** Chosen on test day from `google/gemini-3.1-flash-lite-image`, `google/gemini-3.1-flash-image` and `openai/gpt-5-image-mini`.

### 6. The style preview (B6)

The outline job ends by drawing the deck's look and rendering **three slides by reference-fill with the deck's real words**: the cover, one middle slide and the ask. It costs $0: no model, Chromium only.

The outline gate shows a **style card**:
- the language's name and idea;
- the font pair;
- the palette swatches;
- the image style;
- the three thumbnails;
- **Another style**, which draws a new look and new previews, also free.

This is not a menu: one generated style, changeable (owner, 2026-10-05).

### 7. Measured selection (B9, P1)

`qa/score.py` computes a design score from what QA already measures:
- **balance**: centroid offset;
- **alignment**: the number of distinct left edges and how far each is from the grid;
- **empty-space quality**: one or two large fields, not scattered gaps;
- **clutter**: block count;
- **hero ratio**.

Zero errors is required. `--candidates N` composes N, renders all and keeps the best. The bench reports the median score per deck. The default stays at 1 until test day shows the ranker agrees with the owner.

### 8. Model plumbing (B8)

Compose, image and cheap models are set per run (CLI) and per env (worker). `cli bakeoff --models a,b,c --briefs N` builds the same briefs per model into one wall.

### Design decisions

- **References are adapted, not filled.** A filled template is the fallback only. The model's output keeps the reference's system while fitting this deck's words, tokens and imagery; rotation and within-deck no-repeat keep decks apart. This honours the 2026-10-05 rule (no stored layout reused as-is) and gives the model what every strong system has.
- **The owner's taste gates the library.** Nothing is retrieved until the owner keeps it.
- **Languages are authored, not generated.** A model asked to invent a style produced noise on 2026-10-08. A small set of real systems, varied within, beats an endless set of incoherent ones.
- **Imagery is structural.** Where an image sits is the reference's design decision, not a decoration added afterwards.
- **Charts, numbers and words still win over pictures.** A slide whose job is a number shows the number; images go where the language and the reference place them.

## Verify

- [ ] 1,000 seeds: every language drawn; contrast green; pairings within each language's kinds
- [ ] Every reference passes QA filled long and short under 30 looks of its language
- [ ] Every bench slide (12 outlines) gets a reference of the right shape; reference-fill passes QA for all under 20 looks
- [ ] No compose prompt contains the house-style lines; every one contains its reference
- [ ] Images: a fake transport's bytes become a webp in the slide; a failure leaves a surface field; the export makes zero network requests; image cost in the ledger
- [ ] The style preview renders 3 thumbnails with the deck's words, with no model call
- [ ] **Human (test day):** the owner keeps or drops each reference
- [ ] **Human (test day):** the 12-deck wall — Designed ≥ 4.0, Varied ≥ 4.0, no deck called messy; gate 2 yes ≥ 9/12

## Skipped

- More than 64 references. Trigger: the owner's wall asks for more variety. Growth comes from model-drafted, owner-curated references.
- A vision-model critic. Trigger: the measured ranker disagrees with the owner on more than 30% of pairs.
- Icons. Trigger: sequence or points slides fail on the wall for lack of them.
- Stock-photo sources (Unsplash, Pexels). Trigger: generated images fail the owner's wall.

## Exit gate

- [ ] The test-day wall clears the Verify human line
- [ ] ≤ 3% flagged, ≤ 10% built by code, median ≤ $0.60 a deck, p90 ≤ 5 minutes
- [ ] Median export ≤ 6 MB
