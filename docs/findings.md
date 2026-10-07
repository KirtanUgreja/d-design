# Findings

Facts that cost real work to establish and do not depend on what the product turns out to be. Kept when the version directories were cleared on 2026-08-10, because re-acquiring them costs days and believing a stale version of one costs more.

**This file is evidence, not direction.** Nothing here says what to build. If a finding stops being true, correct it here; if it becomes irrelevant, delete the row rather than leaving it to be cited later.

---

## Measured in this codebase

The output space of the art-direction layer, counted on 2026-08-10 against the three shipped art directions:

| | |
|---|---|
| Font families | **6** — Fraunces, Inter, Newsreader, Archivo, Syne, Space Grotesk |
| Layouts | **6** — full-bleed, split-left, split-right, centered, stack, grid |
| Texture kinds | **6** — grain, halftone, hatch, dither, weave, rule |
| Scene intents | 5 · Motion intents 4 · Colour roles 9 |
| **Art-direction overlap** | **53% identical.** Of 236 distinct value paths, only 112 differ across `cinematic-dark`, `editorial-light` and `bold-brutalist` — the three most deliberately distant designs built in that format |

**Why it matters beyond this codebase:** typography and layout carry more visual identity than colour, and in a system with a brand kit, colour is the axis a viewer attributes to *the brand* rather than to the tool. Whatever the product becomes, the axes that carry identity are the ones worth counting, and they are usually the smallest ones in the system.

**Two architecture lessons from building the second and third art direction:**

- **A token read is the abstraction working; a branch is the abstraction failing.** "Any renderer change means the abstraction is wrong" was too blunt — a hardcoded value becoming a token is the exercise succeeding. A `mode` prop or an `if (id === …)` is it failing.
- **The values a system holds globally are the ones it holds because it only ever had one instance.** Four of the seven costs of the second art direction were exactly this shape, and three more appeared in the third. Expect it wherever a second instance of anything arrives.

**Model CSS is an HTML injection point (2026-10-01).** CSS placed raw in a `<style>` element can close it: `</style><a href=…>` put a full-slide link into the exported deck, and the player advances on click. CSP blocks the script and image variants and cannot block a link. The lint passed it, because tinycss2 tokenises `<` without complaint; it also passed unquoted `url()`, which tinycss2 reads as a `url` token rather than a function. Both were found by proving each payload live on a bare page first, which is the only way a hostile suite means anything.

**Checking numbers in copy (2026-10-01).** Three ways the number check was wrong before it was right, each found on real outlines: a product name ("Tessel 2") read as a statistic at the start of a headline but as a name mid-sentence, so the same deck disagreed with itself — names are now learned from the brief; the same number in two notations ("$50k" and "$50,000") failed to match — numbers are now compared by value; and "Q2" yielded a "2". Numbers written as words ("nine in ten") are still not seen.

## Measured 2026-09-26 — the v1–v3 build

An audit of the code at `8169fd9` and of the three `samples/*.html` decks opened in a browser. It is why v4 exists ([v4/spec.md](v4/spec.md)).

| | |
|---|---|
| What the model could express | A JSON form: ≤6 regions × role/span/emphasis, 5 block kinds. **Never HTML or CSS** |
| What drew every slide | One 265-line `renderer.css`: one type scale, one 12-column grid, a centred column, hierarchy by opacity |
| Design families | 31 on paper, **13 distinct palettes**; three were exact duplicates |
| Fonts | **None loaded.** No `@font-face` anywhere; every named face fell back to a system font |
| How a family was chosen | `sum(ord(title)) % 31`. One trailing space changed the family |
| Brand kit | Zero visual effect: the values never reached the prompt or the renderer |
| Motion | None. `data-reveal` was written and read by nothing |
| Editor canvas | Never loaded the renderer CSS, so it showed browser-default styling |
| Facts | No source. The sample deck's chart was `{"Growth": 85}`; its donut was one colour |
| Headlines | Topic labels: "Visual Data Representation", "Conclusion and Future Outlook" |
| Speaker notes | No field existed |
| Variety gate | Ran against a stub model that wrote the variety itself; it never rendered anything |
| Services | 6 containers, 2 languages, auth split across both, RLS with 3 fix-up migrations, for zero users |
| The stated reason for Python (DSPy/GEPA) | Zero references in the code |

**What every screenshot showed:** a bold heading and one line of text on a flat off-white ground. One slide had a 2.57 MB generated image of a fake chart overflowing the frame; one had a button wrapping one word per line.

**Three lessons:**

- **A rule that forbids the model from designing caps the output at what the renderer can do.** "AI output carries no presentational values" left about five visual variables. The rule was never the safeguard; the token system is.
- **A check that never runs on real output is theater.** The variety gate, the vision critic and the acceptance run all lived outside the product path.
- **Infrastructure built before the output is good is built for nobody.** Accounts, tenancy, quotas and publishing all worked, around decks no one would present.

## Measured 2026-10-07 — removing the exemplars (phase 36)

One deck (`update-q3`, Harbor), `deepseek-v4.1-flash`, against the 2026-10-05 recordings (26 slides, **0** code-built fallbacks).

| Prompt | Reasoning tokens (median) | Cut off | Code-built fallbacks | $/deck |
|---|---|---|---|---|
| compose.v5 (12 exemplars, archetype names) | 3,448 | 0 / 32 | 0 / 8 | ~0.10 |
| compose.v6 (exact geometric target, no exemplars) | 12,000 | 7 / 8 | 7 / 8 | 0.12 |
| compose.v7 (loose target, 12k cap) | ~8,800 | 3 / 8 | 4 / 8 | 0.11 |
| compose.v7 (20k cap) | ~12,400 | 0 / 8 | **3 / 8** (contrast E5 not fixed by 2 repairs) | 0.18 |
| compose.v8 (exact colour pairs, a fresh attempt before the fallback, 20k cap) | ~15,000 | 3 / 8 | 3 / 8 — **every finished slide passed contrast** | 0.16 |
| compose.v9 (`reasoning: minimal`, 12k cap) | still ~12,000 — **ignored** | 5 / 8, 3 empty answers | 5 / 8 | 0.17 |
| **compose.v9 (`low`, 32k cap)** | ~10,100 (max 13,549) | **0 / 8** | **0 / 8**, 0 flagged, 0 near-repeats, 97 s | **0.13** |

- **An exact numeric target makes the model reason until it runs out.** Stated as a direction, it reasons about 2.5× longer than v5, not without end.
- **Without exemplars, the slides the model finishes hold the reference quality; it finishes fewer.** The new failures are contrast on colour fields that repair does not fix.
- **A 32k cap is the fix:** the model needs about 10k tokens of reasoning per slide without examples, and with room to finish it rarely needs repair. Six of eight slides held the reference bar by eye; two (the margin slide, the hire slide) were sparser than their reference counterparts. The owner's wall decides.
- **The cause is the missing examples, not the new steps.** A one-slide A/B (2 slides each): without the three-ideas step, reasoning did not drop (12,000 / 10,200); without the target, it dropped some (9,300 / 4,400) but stayed above v5's 3,400.
- **Exact colour pairs in the rules and in E5 repairs fixed contrast** (v8: every slide the model finished passed).
- **Code-built fallbacks in a row look alike** (three accent panels in a row in the last run): the fallback is a method, and repeated it reads as a template.

### The sameness bench, first run (2026-10-07, no model)

`cli sameness --simulate 30`: 30 code-built decks over the bench outlines, each with its own generated look and targets drawn from a growing archive.

| After | Coverage (625 cells) | Repeats (ε 0.08) | Nearest, median |
|---|---|---|---|
| 3 decks, 23 slides | 2.4% | 13.6% | 0.134 |
| 12 decks, 109 slides | 6.2% | 42.6% | 0.091 |
| 30 decks, 275 slides | **8.0%, flattening** | **65.0%** | 0.059 |

- **The code-built layout is one method, and the bench sees it.** It places one text block (sometimes on a bleeding field) where the target says; it lands within 0.2 on 62% of target descriptors and almost never reaches the canvas edge (median miss 0.34). Fine as a rare last rung; never a source of variety.
- **The model's sameness is still unmeasured.** The exit gate's 30 real decks (~$4) is the run that answers it.
- `distance` takes the closer of the descriptor and occupancy measures, so one coarse agreement counts as a repeat. Whether that is too strict is for the owner's blind wall to say.

## Measured 2026-10-08 — the phase 36/37 gate run

12 outlines from the content engine (`storyline.v4`, `research.v2`; $1.10, inverse spec 0.77, 0 banned words) built 3 times each with generated looks (`build --repeat 3 --outlines 2026-10-08-content`): **36 decks, 327 slides, $5.49** (median $0.14 a deck, 152 s).

| | |
|---|---|
| Slides built by code (fallback) | 3 of 327 |
| Flagged | 0 |
| Novelty retries / near-repeats (W8) | 24 / 13 |
| Decks with a drawn chart | **33 of 36** (51 charts; none before phase 37) |
| Sameness at 100 / 200 / 327 slides | repeats 0.0% / 1.5% / **3.1%**; coverage 6.4% / 9.3% / 10.6% |

- **Phase 36's exit line fails as measured:** repeats 3.1% at 300+ slides and rising, against ≤1% and flat. Coverage is still rising (that line passes). Whether the "repeats" look alike is the owner's blind wall to say: ε (0.08) is unvalidated, and the same outline was built three times on purpose.
- **Most charts are two values** (a before and an after, or two items). The data wall decides whether those beat two figures side by side.

## Research used by v4

Read September 2026.

- **AeSlides** (arXiv 2604.22840): HTML slides scored by four programmatic metrics measured with Playwright — aspect ratio, whitespace, element collision and overflow, visual balance. Training on them beat Claude Sonnet 4.5 and reflection-based systems. **Iterative vision-model reflection was counterproductive**: about 70% of samples stopped after one round despite visible defects.
- **SlideAudit** (arXiv 2508.03630): vision-model judges are weakest on layout flaws and better on contrast. It recommends automated checks plus human review.
- **Learning to Present** (arXiv 2603.16839): the "inverse specification" score — a model rebuilds the brief from the slides alone.
- **OpenRouter web search** (2026-09): the `openrouter:web_search` server tool returns `url_citation` annotations. Exa is about $0.007 per request for 10 results.
- **OpenRouter prompt caching** (2026-09): `cache_control` passes through to Anthropic; cache reads cost 0.1× input.

## Model behaviour

- **Mode collapse is the norm.** LLMs converge to a narrow output space along two dimensions: **intra-model** (repeated samples from one prompt converge on the same idea) and **inter-model** (independently trained models converge on the same idea). Asking one model for three distinct creative artefacts returns three variations of one.
- **Structured output makes it worse.** Instruction tuning against rigid format templates induces measurable diversity collapse; format tokens reduce semantic and lexical diversity.
- **Temperature does not fix it.** Raising temperature and adding "be diverse" to a prompt have *negligible* effect versus structured interventions, and temperature buys token-level diversity at the cost of quality without buying semantic diversity.
- **Therefore: diversity is an architecture problem, not a prompting problem.** Sample the discrete choices outside the model and let the model fill in continuous values within the region it was handed. This also makes diversity *measurable before rendering*, which prompting never can be.
- **Training bias is Western and mainstream**, so collapse is not toward a random point — it is toward the same tasteful default every other tool lands on.
- **Vision is not scarce and not a moat.** ~67 models have it, 28 of them open-weight and self-hostable. Giving a model crop-and-inspect tools is more cost-effective than raising thinking effort on one large image.

Sources: [LLM output diversity](https://arxiv.org/pdf/2604.01504) · [The Price of Format](https://arxiv.org/pdf/2505.18949) · [More Is Not More](https://arxiv.org/html/2607.20429)

**Mapping is model-bound, and the cheap tier cannot do it.** Measured 2026-09-24, one fixed brief and outline, the `scientific` family, four samples per model. The pass/fail rate is the mapping stage's — whether a legal `Deck` came back at all:

| Model | Passed | Best time | Distinct layouts |
|---|---|---|---|
| `openai/gpt-4o-mini` | 0/3 | — | — |
| `openai/gpt-4o` | 3/4 | 6.1s | 5 of 6, 6 of 7, 5 of 7 |
| `anthropic/claude-sonnet-4.5` | 4/4 | 16.1s | 6 of 7, 7 of 7, 7 of 7, 8 of 8 |

Three failure modes, all cross-field consistency the model must hold across a
whole deck at once: a text block with no region in the layout, spans outside
the family's grammar, and a region with no block filling it. The single repair
retry does not recover any of them.

Two things follow. **The mini tier is not a cheaper option for this stage, it
is a broken one** — and it is the *slower* failure, 75.6s before refusing,
because it burns the repair before giving up. And **validity and the product's
claim are the same measurement here**: sonnet returned near-all-distinct
layouts where gpt-4o repeated one, and "it does not look AI-made" is a
statement about layouts, not about prose. The service therefore runs mapping on
sonnet and the cheaper stages on the mini/4o tier (`features/generation/`).

Not yet measured: interview and build reliability per model, and whether a
stronger *prompt* (enumerating the legal spans and the region/block
correspondence explicitly) buys back the mini tier. Both are eval runs, not
opinions.

## The category

Researched August 2026.

- **Gamma** — ~$100M ARR, $2.1B valuation, ~70M users, profitable since 2023, ~50 employees, ~$23M raised before its Series B. Won the mainstream deck market decisively. Its cited weaknesses are *creative ceiling* — generic AI phrasing, limited design control — not speed.
- **Tome** — raised more, reached ~$4M ARR, cut most of a 70-person team in Oct 2024, sunset its presentation product April 2025. Its own retrospective: *"building AI for everyone at once is fundamentally flawed."* It attracted Gen Z, students, freelancers and artists — people who loved it and would not pay. **Its most engaged users were sales and growth professionals**, precisely the segment Gamma targeted deliberately.
- **The structural finding, and the most useful one:** Gamma's most-complained-about defect is that its PowerPoint export breaks — text shifts, spacing changes, fonts substitute. The named cause is that *its layouts are optimised for vertical cards and do not convert cleanly into fixed 16:9 slides*. It also cannot work offline at all. **Both are consequences of a page-shaped product being asked to behave like a deck**, and any page-first architecture inherits them.
- **Scale for reference:** Gamma ships 25+ themes. Canva ships 250,000+ templates.
- **Lossy web-to-PowerPoint export is the category's worst-reviewed feature.** What it loses — web fonts, texture, motion — is what a design-led tool is made of. Native OOXML generation is the only version that does not lose them.

Sources: [Gamma $100M ARR](https://thegtmnewsletter.substack.com/p/how-gamma-grew-to-100m-arr-and-a) · [Why Tome pivoted](https://autoppt.com/blog/tome-app-pivot-away-from-presentations/) · [Gamma export quality](https://www.slidegmm.ai/en/blog/gamma-export-powerpoint-quality-guide)

## Platform

Each carries its status and date because a capability claim without one is unverifiable later.

| | Status | Consequence |
|---|---|---|
| **View Transitions** (same-document) | **Baseline** since Oct 2025 · React 19.2 `<ViewTransition>` | A cross-fade between two states is a state update, not a FLIP implementation |
| **`color-mix()` / OKLCH / relative color** | `color-mix()` Baseline (~89%) · OKLCH ~87% · relative syntax shipped | Colour families derive in CSS at runtime — no build step, no JS colour pass |
| **Container query units** (`cqmin`, `cqw`, `cqh`) | Baseline | A fluid value can be driven by the **frame it is inside** rather than the viewport. This is what makes a fluid design correct in a preview, an editor canvas and a headless renderer simultaneously — a viewport unit is silently wrong in all three |
| **CSS scroll-driven animation** | ~84%; **not Baseline** — Firefox still flagged as of Sept 2025 | Progressive enhancement only. Author the *finished* state as the default so a browser that ignores it shows a complete page, never a blank one |
| **WebGPU** | **Baseline Jan 2026**, ~82%. Three.js `WebGPURenderer` zero-config since r171 | WebGPU primary, WebGL2 fallback, library handles it |
| **APCA** | WCAG 3.0 draft, in Chrome DevTools | **WCAG 2.x cannot evaluate dark backgrounds properly.** Any dark design needs APCA as well, not instead |
| **DTCG token format** | First stable version 2025.10 | A token file interchanges with Figma, Style Dictionary, Tokens Studio for free |
| **CSS logical properties** | Long stable | RTL costs one `dir` attribute *if authored logically from the start*. `transform` is the documented exception, and it is where motion lives |
| **SIL Open Font License** | — | Explicitly permits bundling and embedding in commercial products including SaaS, provided font files are not sold on their own. Covers web delivery, PDF and downloadable bundles. **Verify per family** — "it is on Google Fonts" is not a licence check |
| **EU AI Act Article 50** | **In force 2 August 2026.** Penalties to €15M / 3% of global turnover | Generated text, images **and translations** must be marked machine-readably. C2PA is the mechanism the Commission's draft Code of Practice names |

## Process

Three things that were learned by getting them wrong, and that are not about this product.

**The quality apparatus verified structure, and every real defect was presentational.** A schema, a linter, a type checker and an invariants script all passed on output that was plainly not good enough — scenes with no frame, gradients where they were banned, images rendering as grey rectangles, eight identical centred layouts in a row. **Automated gates cannot see design.** Something has to look at the output, and it has to happen earlier than feels necessary.

**A gap two documents agree on can still belong to nobody.** One defect was recorded honestly, twice, as a deferral — and then picked up by no phase in the next release. A deferral without an owner and a trigger is a decision to never do it.

**A decision filed under the wrong heading is a decision that does not apply.** A ban on gradients lived in the design directory, which everyone read as being about our own surfaces, so the generated output was exempt by *filing* rather than by *decision*. Where a rule lives determines what it governs.
