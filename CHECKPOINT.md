# Checkpoint — 2026-10-01

Resume point. Branch `phase-22-engine-spike`. `main` is still v3 (`8169fd9`, also tagged `v3-final`).

## Where things stand

| | |
|---|---|
| Plan | `docs/v4/` — the model designs each slide in HTML inside theme tokens. Phases 21–29 |
| Phase 21, built | v3 code deleted. `api/` is the v4 skeleton: data models, the model seam (`engine/llm/openrouter.py`, 13 regression tests), settings, the CLI, the bench tools. New gate (ruff, mypy --strict, pytest, docs), light post-edit hook, CI. 12 bench briefs with frozen outlines, rubric, the wall builder |
| Phase 21, open | 2 of 12 one-shot baselines failed with HTTP 402: **the OpenRouter credit ran out**. Gamma baselines (owner). The owner's ratings of the baseline wall |
| Spent so far | $3.30 of model credit |

## Owner's tasks to close phase 21

1. Done 2026-10-01: all 12 one-shot baselines, on DeepSeek.
2. Gamma baselines: dropped for now (owner, 2026-10-01).
3. `cd api && uv run python -m cli wall --run 2026-09-30-baselines`, open `bench/runs/2026-09-30-baselines/wall.html`, rate every deck, download `ratings.json` into that folder.

## Phase 22, in progress (branch `phase-22-engine-spike`)

Built: 3 themes, 8 vendored OFL font families, 12 exemplars, sanitizer (nh3), CSS lint (tinycss2), one shadow root per slide, browser QA (`engine/qa/measure.js`), compose + one targeted repair + a code-built fallback, the minimal export, `cli build`.

First comparison (`bench/runs/2026-09-30-models/wall.html`): DeepSeek v4.1 Flash, Gemini 3.8 Flash and GLM 5.3 Flash, 3 decks each, against the baselines. $0.02–0.06 per deck.

Owner inspected the decks and approved the quality (2026-09-30). Model pinned: `deepseek/deepseek-v4.1-flash`. The fallback is now three designed code layouts. Full 12-deck run: `bench/runs/2026-09-30-full/wall.html` — $0.67 total, median $0.055 per deck, nothing flagged.

Exemplar A/B done: keep the library (fewer repairs, near-zero cost). Images deferred to phase 25 (owner, 2026-10-01): no frozen outline asks for one. Verify suites built 2026-10-01: hostile slides, one fixture per QA code, the offline test; the hostile suite found and closed a `</style>` breakout in model CSS. One-shot baselines rebuilt on DeepSeek, all 12 (2026-10-01, $0.38). Gate 1, attempt 1 (2026-10-01): failed on one line — preferred in 8 of 12 pairs, needs 9; the rest passed (`bench/results.md`). Owner chose attempt 2: design fixes (no empty accent blocks, nightshift tuned, more variety inside a deck), rerun 12, re-rate blind. A second failure means the exemplar-fill pivot. Attempt 2 (2026-10-01): failed — 6 of 12 preferred, 7 of 12 usable. The engine wins Designed and loses Says something; rater drift on identical decks is as large as the gap (`bench/results.md`). Owner decided (2026-10-01): phase 22 closes on design, no exemplar-fill pivot; phase 24 next, before 23, and gate 2 re-tests against the one-shot.

## Phase 24, built (branch `phase-24-content-engine`)

`engine/content/`: rules, arcs, research (no quote, no fact), storyline, interview, notes. CLI: `outline --brief ID` (the gate), `content --run NAME` (bench), `injection --run NAME`. Bench `2026-10-01-content`: every automated exit line passes, about $0.08 per outline. **Owner's tasks:** read `bench/runs/2026-10-01-content/review.md` — are 5 of 6 outlines approvable with ≤3 edits? Open the 20 facts — is each number in its quote, and the quote on the page? Try `cd api && uv run python -m cli outline --brief launch-product` for the interactive gate. Gamma baselines dropped for now (owner, 2026-10-01). OpenRouter credit left: $0.40 (2026-10-01).

Budget: the owner set a $10 cap and cheap paid models only (no free ones). About $1.30 of credit was left on 2026-09-30.

## Next

Phase 22 (`docs/v4/plan/22-engine-spike.md`) — the make-or-break gate. It needs credit: its budget cap is $100, and a full 12-deck run is about $15.

## Phase 23, built (branch `phase-24-content-engine`)

33 OFL families measured, 7 OKLCH palettes (0 contrast failures in 1,000 seeds), 24 pairings, 5 grids, 10 motifs, a seeded sampler, brand mapping, style tiles. 12 decks on sampled themes: 0 flagged, $0.66. Gate: 9 of 10 pairings (chance; see `bench/results.md`). **Owner's tasks:** `bench/runs/2026-10-01-phase23/tiles.html` (36 looks: ≥30 usable, no sibling trios) and `wall.html` (no two decks mistakable).

## Phase 26, built (branch `phase-26-player-export`)

The real player (`api/engine/export/player.js`, `player.css`): arrows, Space, PgUp/PgDn, Home/End, number + Enter, swipe, click, F, O overview, B black, `#n`, P presenter popup (current, next, notes, timer, clock; keys work in either window), step reveals with reduced motion. `assemble.py`: "present" (notes as inert JSON) and "send" (none); AI metadata, export SHA-256 logged, disclosure in the chrome. `pdf.py` prints "send". `cli export --run NAME [--pdf]` re-assembles built decks for $0. CI now installs Chromium, Firefox and WebKit — before this, every browser test would have failed there. **Owner's tasks:** present `bench/runs/2026-10-01-phase23/engine/<brief>/deck.html` on a laptop with an external display and a clicker (press P for the presenter view); open a `deck-send.html` from an email attachment in 3 browsers.

## Phase 25, the free half (branch `phase-25-composition-qa`)

Charts from approved facts (bar, column, line, donut; golden files), the planner's 10 archetypes and rhythm rules, the repair ladder (2 rounds → exemplar-fill → code layout → flag), a budget guard in the seam that fails closed, E5 on real pixels and warnings W1–W6. 67 tests green. **Needs credit next:** `dd-image` and its bake-off, the 12 briefs × 2 seeds end-to-end run, and gate 2 (owner).
