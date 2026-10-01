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

1. Top up OpenRouter, then: `cd api && uv run python -m cli baseline --set all` (only the 2 missing decks are generated).
2. Gamma baselines: dropped for now (owner, 2026-10-01).
3. `uv run python -m cli wall --run 2026-09-30-baselines`, open `bench/runs/2026-09-30-baselines/wall.html`, rate every deck, download `ratings.json` into that folder.

## Phase 22, in progress (branch `phase-22-engine-spike`)

Built: 3 themes, 8 vendored OFL font families, 12 exemplars, sanitizer (nh3), CSS lint (tinycss2), one shadow root per slide, browser QA (`engine/qa/measure.js`), compose + one targeted repair + a code-built fallback, the minimal export, `cli build`.

First comparison (`bench/runs/2026-09-30-models/wall.html`): DeepSeek v4.1 Flash, Gemini 3.8 Flash and GLM 5.3 Flash, 3 decks each, against the baselines. $0.02–0.06 per deck.

Owner inspected the decks and approved the quality (2026-09-30). Model pinned: `deepseek/deepseek-v4.1-flash`. The fallback is now three designed code layouts. Full 12-deck run: `bench/runs/2026-09-30-full/wall.html` — $0.67 total, median $0.055 per deck, nothing flagged.

Exemplar A/B done: keep the library (fewer repairs, near-zero cost). Images deferred to phase 25 (owner, 2026-10-01): no frozen outline asks for one. Verify suites built 2026-10-01: hostile slides, one fixture per QA code, the offline test; the hostile suite found and closed a `</style>` breakout in model CSS. Left in phase 22: only the owner's blind ratings, which need the 2 missing one-shot baselines (about $0.50 on Opus; $0.40 left). Gamma baselines dropped for now (owner, 2026-10-01). OpenRouter credit left: $0.40 (2026-10-01).

Budget: the owner set a $10 cap and cheap paid models only (no free ones). About $1.30 of credit was left on 2026-09-30.

## Next

Phase 22 (`docs/v4/plan/22-engine-spike.md`) — the make-or-break gate. It needs credit: its budget cap is $100, and a full 12-deck run is about $15.
