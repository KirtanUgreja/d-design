# v4 — designed, not assembled

> The release where the model designs. A founder types a brief and gets a deck that looks designed and says something: each slide composed in real HTML inside a per-deck design system, measured in a real browser, grounded in cited facts, and exported as one offline file. Decided 2026-09-26 after an audit of the v1–v3 build.

## What this release is

v1–v3 built a pipeline, an editor, accounts and billing. Every deck still came out as a bold heading and one line of text on a flat background.

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

## Find it fast

| If you need… | Go to |
|---|---|
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
| How our own app looks (not the decks) | [../design/app.md](../design/app.md), [../design/brand.md](../design/brand.md) |
