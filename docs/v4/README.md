# v4 — designed, not assembled

> The release where the model designs. A founder types a brief and gets a deck that looks designed and says something: each slide composed in real HTML inside a per-deck design system, measured in a real browser, grounded in cited facts, and exported as one offline file. Decided 2026-09-26 after an audit of the v1–v3 build.

## What this release is

v1–v3 built a pipeline, an editor, accounts and billing. Every deck still came out as a bold heading and one line of text on a flat background ([../findings.md](../findings.md) → "Measured 2026-09-26").

v4 rebuilds the product around the one thing that was missing:
- **The model composes each slide in HTML and CSS**, within theme tokens.
- **Automatic browser checks** stop broken slides.
- **A content engine** writes storylines from cited facts.

The app is rebuilt around that flow: composer → interview → outline → watch slides stream in a look generated for the deck → edit → present or export. Accounts come last.

## Files

| File | What's in it |
|---|---|
| [README.md](README.md) | This map |
| [spec.md](spec.md) | Decisions, commitments, bets with falsifiers, what changes from v3, and risks |
| [engine.md](engine.md) | The pipeline, the backend and frontend layout, the data model, generation events, the model seam, and the security of AI-written HTML |
| [content.md](content.md) | The interview, research and the `Fact` ledger, storyline arcs, content rules, and content evals |
| [design-engine.md](design-engine.md) | The design-system registry, the sampler and theme, compositions and exemplars, the slide contract, the lint, QA metrics and repair |
| [bench.md](bench.md) | The 12 briefs, the baselines, the wall, the rubric, what each run records, and the budgets |
| [ui-research.md](ui-research.md) | The user side: attention, motivation and trust, the evidence behind each technique, competitors, ten rules, and the ethics line |
| [research-2026-10.md](research-2026-10.md) | 2026-10-08: Gamma 5, the competitors and the 2024–26 papers on slide design; why our decks looked alike or messy |
| [plan/README.md](plan/README.md) | Phase status, dependency graph, build order |
| [plan/21-reset.md](plan/21-reset.md) | Phase 21 — delete what v4 replaces, set the rules and the gate, build the bench |
| [plan/22-engine-spike.md](plan/22-engine-spike.md) | Phase 22 — decks that look designed, from the CLI, on frozen outlines. **The make-or-break gate** |
| [plan/23-design-system.md](plan/23-design-system.md) | Phase 23 — fonts, palettes, grids, motifs, the look generator, brand colours |
| [plan/24-content-engine.md](plan/24-content-engine.md) | Phase 24 — interview, research, storyline, notes, content evals |
| [plan/25-composition-qa.md](plan/25-composition-qa.md) | Phase 25 — planner, exemplar library, charts, images, the full QA loop. **The second human gate** |
| [plan/26-player-export.md](plan/26-player-export.md) | Phase 26 — the offline player, presenter view, export, PDF |
| [plan/27-app-create-flow.md](plan/27-app-create-flow.md) | Phase 27 — the new web app: composer → interview → outline → looks → streaming watch |
| [plan/28-editor.md](plan/28-editor.md) | Phase 28 — the editor: inline edits, AI edits per slide, design tweaks, versions |
| [plan/29-accounts-deploy.md](plan/29-accounts-deploy.md) | Phase 29 — accounts, Postgres, cost metering, budget caps, deploy |
| [plan/30-ui-prototype.md](plan/30-ui-prototype.md) | Phase 30 — the five hot surfaces as a clickable prototype on real decks, tested with 5 users; the UI baseline. No credit |
| [plan/31-first-run.md](plan/31-first-run.md) | Phase 31 — the first minute: a $0 recorded demo, a brief that survives sign-up, their cover within a minute |
| [plan/32-watch-reveal.md](plan/32-watch-reveal.md) | Phase 32 — the peak and the end: the cover first, real work visible, a reveal worth showing |
| [plan/33-trust-control.md](plan/33-trust-control.md) | Phase 33 — provenance you can open, AI changes as proposals, labelled undo, resume |
| [plan/34-presenter-confidence.md](plan/34-presenter-confidence.md) | Phase 34 — rehearse mode, pacing against their minutes, a ready check |
| [plan/36-independent-design.md](plan/36-independent-design.md) | Phase 36 — no stored layouts: per-slide composition targets in unexplored design space, a novelty archive, continuous palettes and variable fonts. Before gate 2 |
| [plan/35-measure-learn.md](plan/35-measure-learn.md) | Phase 35 — content-free funnel events, monthly user tests, the ethics gate, a UI scorecard |

## Find it fast

| If you need… | Go to |
|---|---|
| Why the v1–v3 decks looked bad | [../findings.md](../findings.md) → "Measured 2026-09-26" |
| What v4 proves, and how we would know it failed | [spec.md](spec.md) → Theme, Bets |
| Why the model may now write CSS, and what it may not write | [spec.md](spec.md) → Locked decisions → Token rule; [design-engine.md](design-engine.md) → "Slide lint" |
| Where a module goes, backend or frontend | [engine.md](engine.md) → "Layout" |
| The Pydantic models (`Brief`, `Fact`, `SlidePlan`, `Theme`, `Slide`, `Deck`…) | [engine.md](engine.md) → "Data model" |
| What streams to the browser during generation | [engine.md](engine.md) → "Generation jobs and events" |
| How AI-written HTML is made safe | [engine.md](engine.md) → "Security of AI-written HTML" |
| The interview questions | [content.md](content.md) → "Interview" |
| Where numbers come from, and how they are cited | [content.md](content.md) → "Research and the Fact ledger" |
| The storyline arc for a pitch, sales, launch, update or partnership deck | [content.md](content.md) → "Arcs" |
| Banned phrases and headline rules | [content.md](content.md) → "Content rules" |
| How a deck gets its look, and why two decks differ | [design-engine.md](design-engine.md) → "Registry", "Sampler" |
| The composition intents and the exemplar library | [design-engine.md](design-engine.md) → "Compositions", "Exemplars" |
| QA thresholds (overflow, contrast, min type size…) | [design-engine.md](design-engine.md) → "QA metrics" |
| How to run the bench and score the wall | [bench.md](bench.md) |
| Cost and latency per deck | [bench.md](bench.md) → "Budgets" |
| Which phase is next | [plan/README.md](plan/README.md) |
| How our own app looks (not the decks) | [../design/app.md](../design/app.md), [../design/brand.md](../design/brand.md) |
