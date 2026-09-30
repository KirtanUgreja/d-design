# Bench results

One row per run (docs/v4/bench.md -> "What a run records"). Runs themselves live in `bench/runs/`, which is ignored.

| Date | Run | What | Decks | Cost | Latency | Owner's ratings |
|---|---|---|---|---|---|---|
| 2026-09-30 | `2026-09-30-baselines` | One-shot baseline, `anthropic/claude-opus-5.5`, prompt `bench-oneshot.v1` | 10 of 12 — `launch-product` and `pitch-health` failed with HTTP 402 (OpenRouter credit ran out) | median $0.21 per deck, $3.11 total | median 93 s, max 213 s | pending |
| 2026-09-30 | — | Frozen outlines, `anthropic/claude-sonnet-5.5`, prompt `bench-outline.v1` | 12 of 12, all parsed first time | $0.01–0.025 each, $0.19 total | — | — |
| 2026-09-30 | — | v3 samples, screenshotted before deletion | 3 | — | — | pending |
| 2026-09-30 | `2026-09-30-models` | Engine, phase 22, prompt `compose.v1`, 3 smoke briefs × 3 themes. `deepseek/deepseek-v4.1-flash` | 3 | median $0.057 per deck | median 58 s | pending. 26 of 30 slides clean first pass, 3 fell back to the code layout, 0 flagged |
| 2026-09-30 | `2026-09-30-models` | Same, `google/gemini-3.8-flash` | 3 | median $0.049 | median 52 s | pending. 22 of 30 clean first pass, 3 fallback, 0 flagged |
| 2026-09-30 | `2026-09-30-models` | Same, `z-ai/glm-5.3-flash` | 3 | median $0.018 | median 69 s | pending. 15 of 30 clean first pass, 6 fallback, 0 flagged |
| 2026-09-30 | — | `qwen/qwen3.8-flash` | 0 | — | stalled for over 10 minutes on the first deck; dropped | — |
| 2026-09-30 | `2026-09-30-full` | Engine, all 12 briefs, `deepseek/deepseek-v4.1-flash`, `compose.v1`, three-layout fallback | 12 of 12 | median $0.055, total $0.67 | about 1 minute per deck | owner looked at the decks and approved the quality; no ratings file. 0 slides flagged |
| 2026-09-30 | `2026-09-30-ab` | Exemplar A/B: the 3 smoke briefs **without** exemplars, DeepSeek | 3 | median $0.061 | 45–89 s | owner to compare. 21 of 30 slides clean first pass (26 of 30 with exemplars in `2026-09-30-models`), 2 fallback, 0 flagged |

**The bar phase 22 has to beat:** a single prompt to the best model costs about $0.21 and 93 seconds per deck, and already looks far better than v3. It also shows the look v4 is built to avoid: rounded cards, numbered badges, one centred system font.

**First engine result (2026-09-30):** on cheap models a deck costs $0.02–0.06, about a quarter of the one-shot baseline's $0.21 on the top model, and finishes in about a minute with no defect left. The weak point is the code-built fallback layout, which about 1 slide in 10 ends up with: it is never broken, and it is plain.

**Exemplar A/B (2026-09-30):** without the library the model still designs well, but more slides need a repair (9 of 30 against 4 of 30). The library costs almost nothing, because it sits in the cached prefix. Decision: keep it. Two caveats: 3 decks is a small sample, and the with/without decks were not on the same themes, so the look cannot be compared slide for slide.
