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
3. `uv run python -m cli wall --run 2026-09-30-baselines`, open `bench/runs/2026-09-30-baselines/wall.html`, rate every deck, download `ratings.json` into that folder.

## Phase 22, in progress (branch `phase-22-engine-spike`)

Built: 3 themes, 8 vendored OFL font families, 12 exemplars, sanitizer (nh3), CSS lint (tinycss2), one shadow root per slide, browser QA (`engine/qa/measure.js`), compose + one targeted repair + a code-built fallback, the minimal export, `cli build`.

First comparison (`bench/runs/2026-09-30-models/wall.html`): DeepSeek v4.1 Flash, Gemini 3.8 Flash and GLM 5.3 Flash, 3 decks each, against the baselines. $0.02–0.06 per deck.

Owner inspected the decks and approved the quality (2026-09-30). Model pinned: `deepseek/deepseek-v4.1-flash`. The fallback is now three designed code layouts. Full 12-deck run: `bench/runs/2026-09-30-full/wall.html` — $0.67 total, median $0.055 per deck, nothing flagged.

Exemplar A/B done: keep the library (fewer repairs, near-zero cost). Images deferred to phase 25 (owner, 2026-10-01): no frozen outline asks for one. Verify suites built 2026-10-01: hostile slides, one fixture per QA code, the offline test; the hostile suite found and closed a `</style>` breakout in model CSS. One-shot baselines rebuilt on DeepSeek, all 12 (2026-10-01, $0.38). Gate 1, attempt 1 (2026-10-01): failed on one line — preferred in 8 of 12 pairs, needs 9; the rest passed (`bench/results.md`). Owner chose attempt 2: design fixes (no empty accent blocks, nightshift tuned, more variety inside a deck), rerun 12, re-rate blind. A second failure means the exemplar-fill pivot. Attempt 2 built 2026-10-01 ($0.64, nothing flagged); its blind wall is `bench/runs/2026-10-01-attempt2/wall.html`, waiting on the owner's ratings. Gamma baselines dropped for now (owner, 2026-10-01). OpenRouter credit left: $0.40 (2026-10-01).

Budget: the owner set a $10 cap and cheap paid models only (no free ones). About $1.30 of credit was left on 2026-09-30.

## Next

Phase 22 (`docs/v4/plan/22-engine-spike.md`) — the make-or-break gate. It needs credit: its budget cap is $100, and a full 12-deck run is about $15.
