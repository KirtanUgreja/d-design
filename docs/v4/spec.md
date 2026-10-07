# v4 — spec

## Theme

**One paragraph. What this release proves that the last one did not.**

v1–v3 proved a pipeline could run end to end and export an offline file. They never produced a deck that looks designed. The audit of 2026-09-26 found why ([../findings.md](../findings.md) → "Measured 2026-09-26"):
- The model was not allowed to design: non-negotiable #7 limited it to filling a JSON form.
- Everything visual came from one 265-line stylesheet whose fonts never loaded.
- Content had no source of facts.

v4 proves the claim the product exists for. **A founder types a brief and gets a deck a designer would not be embarrassed by:**
- composed by the model in real HTML inside a per-deck design system
- checked in a real browser before anyone sees it
- grounded in cited facts
- exported as one offline file

Accounts, billing and hosting wait until that is true on a wall of 12 decks.

## Commitments vs bets

### Commitments

| Commitment | Why it holds |
|---|---|
| **The artefact is one self-contained `.html` file with zero network requests.** Fonts, images, charts and the player are embedded | It is the product. A browser test from `file://` proves it on every change |
| **The model composes every slide in HTML and CSS. Colour and type come only from the deck's theme tokens** | HTML's freedom is the differentiator; the token rule is what keeps 12 separately generated slides one deck |
| **Charts, images and textures are components the model places, never draws** | Data stays true. The v3 sample's model-drawn "chart image" was fake data |
| **The engine must beat one prompt to the same model.** A deck from "make a 10-slide HTML deck about X" on the best model is the baseline on every wall | If orchestration can't beat a single prompt, it is overhead ([bench.md](bench.md) → "Baselines") |
| **Every slide is rendered in Chromium and measured before a user sees it** | [../findings.md](../findings.md) → Process: structure checks passed on visibly broken decks |
| **No gradients, neon, blur or glow in generated output.** Colour changes through texture | Standing owner rule; [../design/principles.md](../design/principles.md) §5 governs the artefact |
| **Every number is traceable to the user (YOU) or a cited source (WEB), or flagged for the user to confirm** | The first users present to skeptics. One invented number costs the deck |
| **A human scores the bench wall at every phase exit** | Automated gates cannot see design. It is the owner's decision (2026-09-26) |
| **Output quality before infrastructure** | v1–v3 built RLS, teams, quotas and publishing around decks that were not good |
| **A plain orchestrator, no agent framework** | Unchanged from v1. Every next step is our code's decision |
| **Python backend, Next.js frontend. The backend owns the engine, data and export; the frontend is UI only** | Owner's decision (2026-09-26). One owner per concern ends the split auth and the second renderer |

### Bets

| Bet | What would disprove it |
|---|---|
| **A top model composing HTML inside a token system with curated exemplars produces decks that read as designed, not AI-made** | The owner scores the phase-22 smoke set below 4/5 on "looks designed" after three prompt/exemplar/model iterations |
| **A seeded sampler over discrete axes (type pairing, palette strategy, grid, motif) makes decks mutually distinguishable** | On the 12-deck wall the owner mistakes any two decks for the same look |
| **Browser metrics plus a targeted repair remove visible defects without a vision-model judge** | The owner finds a visible defect on the wall that no metric flagged, in two consecutive phase exits |
| **Web research with citations makes decks say something** | Content score below 4/5, or a 20-fact spot check finds more than one wrong fact |
| **The interview earns its 60 seconds** | Decks from skipped interviews score the same as decks from answered ones |
| **Roughly $0.8–2 per 10-slide deck (estimate) is acceptable for a quality-first product** | Phase 22 measures a median above $3 per deck with no clear path down |
| **Orchestration beats a single prompt** | At phase 22 the one-shot baseline is preferred in more than 3 of 12 blind pairs |
| **A fixed 16:9 canvas, scaled to fit, is fine for presenters** | Letterboxing becomes the most common complaint |
| **Founders and salespeople will choose better over faster** | In side-by-side trials after phase 28, early users pick Gamma's speed over our output |

## Locked decisions

| Axis | Decision | Why |
|---|---|---|
| **Slide authoring** | The model writes each slide as an HTML fragment plus scoped CSS | Owner's decision (2026-09-26). The JSON form capped the output at about five visual variables |
| **Token rule** | Colour, `font-family`, `font-size` and `font-weight` may only reference the theme (`var(--…)` or an embedded weight). Layout values are free | Cohesion and reskinning, without taking composition away from the model. Replaces non-negotiable #7 ([../coderules/README.md](../coderules/README.md)) |
| **Canvas** | Fixed **1920×1080**, scaled to fit the screen, letterboxed in the slide's own ground colour | QA must render one deterministic size. Reverses v2's fluid frame |
| **Stack** | FastAPI (Python 3.13) owns the engine, the data and the export. Next.js (TypeScript) is UI only. API types are generated from OpenAPI | Owner's decision. It removes the second renderer and the Deck codegen |
| **Model gateway** | OpenRouter; one model per stage, set in settings; quality first | The key exists, and a model swap is a config change. Models are chosen by the phase-22 bake-off |
| **Diversity** | **Every deck gets its own generated look; the user never picks one.** A seeded generator draws the few discrete choices (a font pairing, a grid) and makes everything else continuous — the whole palette, type-scale ratios, margins, rule weight, tracking, texture geometry — steered by the deck's own words and tone, plus a signature mark drawn from its title. **Code, no model call.** *Reversed 2026-10-05 by the owner:* "three looks to pick from" was a smaller template gallery. **Next (same day):** per-slide compositions must be independent too — no exemplars or archetype menus in the prompt; generated toward unexplored design space and checked against an archive ([plan/36-independent-design.md](plan/36-independent-design.md)) | [../findings.md](../findings.md) → Model behaviour: diversity is architecture, not prompting. OKLCH palettes, type scales and grids are maths, and a model would add cost, mode collapse and contrast bugs |
| **QA** | Render in Playwright → measure DOM and pixels, including a computed-style check → targeted repair (at most 2 rounds) → exemplar-fill fallback → visible flag. **A failure to measure is an error** | AeSlides (arXiv 2604.22840) beat VLM reflection with exactly these measurable metrics |
| **Process model** | Model calls, Chromium and image work run in `api/worker.py` from phase 27. The internet-facing API never calls a model or a browser, and never holds the key. The CLI drives the engine before phase 27 | Chromium work would stall the API's event loop and SSE streams, a reload or deploy would kill paid generations mid-flight, and a browser crash stays in the worker |
| **Slide scoping** | One Declarative Shadow DOM root per slide (`<template shadowrootmode>`, Baseline 2024). CSS is linted, never rewritten | Theme tokens and fonts still reach inside; model CSS cannot leak out; the same fragment renders identically in QA, the editor and the export |
| **Facts** | `openrouter:web_search` citations plus pasted material go into a `Fact` ledger; every claim carries YOU / WEB / AI provenance | Owner's decision (2026-09-26) |
| **First users** | Founders and sales. Five deck types: pitch, sales, launch, investor update, partnership | Owner's decision. Tome's post-mortem: "AI for everyone at once" was the flaw |
| **Human review** | The bench wall at every phase exit | Owner's decision |
| **Storage** | A file store behind one Python data module until phase 29; after that, Postgres owned only by Python | Nothing needs a database before users exist |
| **Auth (phase 29)** | A managed provider. FastAPI verifies the JWT against JWKS; no table is shared across languages | Ends v3's split auth, where web stripped the cookie and Python read `auth.session` |
| **AI-written HTML security** | `nh3` allowlist, then `tinycss2` lint and scoping, then a script-less sandboxed iframe in the app, then an export CSP of `default-src 'none'` | Three independent layers; details in [engine.md](engine.md) → "Security of AI-written HTML" |
| **Export** | One file: our player (script allowed by hash), vendored Latin-subset fonts embedded once as-is, webp images, machine-readable AI markers. **Two flavours: "present"** (speaker notes for the presenter view) **and "send"** (no notes; the PDF is made from send) | The product. Emailing a file must never leak the notes. Per-deck font subsetting is deferred: subsetting counts as modification under the OFL, and vendored subsets are already 20–60 KB per style. EU AI Act Art. 50 has been in force since 2026-08-02 |
| **What slides may contain** | Text in fields, `dd-image`, `dd-chart`, `dd-texture`. **No links, no icons, no model-written animation** — URLs are plain text, and the player owns motion | Removes v3's `javascript:` class entirely. The icon + heading + blurb card is the single most legible "AI deck" tell |
| **Presenting** | The present mode shows the export file itself | What you present is byte-for-byte what you send |
| **PPTX** | Not built | Trigger: repeated user demand. Approach then: DOM-measured HTML→PPTX |

## What changes from v3

| Old | New | Why |
|---|---|---|
| The model fills a JSON form; one 265-line stylesheet renders every slide | The model composes HTML per slide within the theme tokens | Output was capped at about five visual variables |
| 31 "families" (13 palettes) picked by `sum(ord(title)) % 31`; fonts never loaded | A sampler over ~40 embedded OFL families, palette strategies, grids and motifs; 3 looks shown to the user | The design system was a lookup table |
| No facts, topic-label titles, no speaker notes | Research into a `Fact` ledger, assertion headlines, notes on every slide | The content said nothing |
| `gpt-4o-mini` rewrote Sonnet's copy, one slide at a time, with no context | A top model composes each slide with the storyline, theme and exemplars in view | Spend went to the wrong stage |
| Vision critic in the CLI only; variety gate on a stub model | Browser-measured QA in the product path; a bench wall with human scores | Checks that never ran on real output were theater |
| Fluid `100vh` pages | A fixed 1920×1080 canvas, scaled | Deterministic QA |
| 6 containers, split auth, RLS, teams, quotas, MinIO, upload worker | FastAPI + Next.js + a file store; accounts in phase 29 only | Built for users who did not exist |
| One web page; export downloaded `deck.json` | Composer → interview → outline → looks → streaming watch → editor → present / export | The CLI exposed more of the product than the app |
| Pydantic `Deck` → TS types + Zod codegen | OpenAPI → TS types for API payloads; slides are HTML | There is no second renderer to feed |
| Phases 00–20 | Phases 21–29 | [../versions.md](../versions.md): a phase number is a filename, and numbers append |

## Risks

1. **Model-written HTML converges on the "AI HTML look"** (dark cards, icon rows, rounded boxes). → Curated exemplars, the anti-default lint, sampler axes and the wall. Retired when the phase-25 wall passes.
2. **Cost or latency is too high.** → Prompt caching (stable prefix first), 5-way parallel slides, a cheaper model for repair and notes, and a per-deck `budget_usd` cap that fails closed. Retired when phase 25 measures a median ≤ $2, a p90 ≤ 5 minutes and a first slide within 60 seconds of approval.
3. **Metrics miss real defects.** → The human wall at every exit, and every miss becomes a new metric. Stays open.
4. **Wrong facts.** → Citations on the slide, a spot check per bench run, flagged numbers. Retired when three consecutive spot checks are clean.
5. **A theme re-roll breaks existing slides.** → QA and repair on every swap, with regeneration as the fallback. Retired in phase 28 if under 30% of slides need repair after a swap.
6. **Sanitizer or CSP bypass.** → Three layers and an XSS corpus test. Stays open.
7. **The v1–v3 failure repeats: infrastructure before quality.** → Phase order, and the phase-22 human gate that blocks everything after it. Retired at phase 25's exit.
8. **The owner's review time becomes the bottleneck.** → Walls take ≤ 15 minutes (the phase-22 gate, with baselines, takes about 30), and the 3-deck smoke set covers the work between exits. Stays open.
9. **Model drift.** OpenRouter model ids change underneath us. → Model ids are pinned in settings, and any change re-runs the bench. Stays open.
10. **The exemplar library becomes a time sink.** → Exemplars grow past 12 only if phase 22's with/without A/B shows they help. Retired at phase 22's exit either way.
