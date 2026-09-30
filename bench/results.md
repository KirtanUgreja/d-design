# Bench results

One row per run (docs/v4/bench.md -> "What a run records"). Runs themselves live in `bench/runs/`, which is ignored.

| Date | Run | What | Decks | Cost | Latency | Owner's ratings |
|---|---|---|---|---|---|---|
| 2026-09-30 | `2026-09-30-baselines` | One-shot baseline, `anthropic/claude-opus-5.5`, prompt `bench-oneshot.v1` | 10 of 12 — `launch-product` and `pitch-health` failed with HTTP 402 (OpenRouter credit ran out) | median $0.21 per deck, $3.11 total | median 93 s, max 213 s | pending |
| 2026-09-30 | — | Frozen outlines, `anthropic/claude-sonnet-5.5`, prompt `bench-outline.v1` | 12 of 12, all parsed first time | $0.01–0.025 each, $0.19 total | — | — |
| 2026-09-30 | — | v3 samples, screenshotted before deletion | 3 | — | — | pending |

**The bar phase 22 has to beat:** a single prompt to the best model costs about $0.21 and 93 seconds per deck, and already looks far better than v3. It also shows the look v4 is built to avoid: rounded cards, numbered badges, one centred system font.
