# Phase 21 — reset

> This phase makes the repository match the decision: everything v4 replaces is gone, the rules and the gate describe the new shape, and a calibrated quality bar exists before any engine code is written.

**Depends on:** — · **Blocks:** 22 · **Spec step:** What changes from v3 · **Size:** M

## Search

**Read first** — [../spec.md](../spec.md) (all), [../engine.md](../engine.md) → Layout, [../bench.md](../bench.md), [../../coderules/README.md](../../coderules/README.md) → Non-negotiables, [../../coderules/commits.md](../../coderules/commits.md)

**Grep for**
- `docs/v1`, `docs/v2`, `docs/v3` across the repo — no live pointer may remain.
- `invariants.sh` in `scripts/hooks/*` and `.github/` — every caller goes with it.
- `AGENTS.md` in `.gitignore` — `CLAUDE.md` imports it, so a fresh clone gets a dangling import.

**Verify externally**
- OpenRouter: the `usage` cost field, prompt-caching passthrough and the minimum cacheable prefix for the candidate models, current list prices.
- Which top models are available under the existing key.

## Make

**Docs (done 2026-09-30):** `docs/v4/`, and the v4 updates to `docs/coderules`, `docs/techstack`, `docs/security`, `docs/design`, `docs/findings.md`, `docs/README.md`, `README.md`, `AGENTS.md`, `CHECKPOINT.md`. `docs/v1`–`v3` deleted.

**Before deleting anything:** tag the current head `v3-final`, screenshot the three `samples/*.html` decks into `bench/baselines/v3/`, and copy the five golden briefs out of `api/pipeline/acceptance/briefs.py`.

**Delete:**
- `web/`, `render/`, `worker/`, `docker-compose.yml`, `samples/`.
- In `api/`: `schema/{deck,grammars,design_families,no_style,critic}.py`, `pipeline/`, `features/`, `auth/`, `db/`, `migrations/`, `alembic.ini`, `Dockerfile`, the old `cli.py`, and the tests of deleted modules.
- `scripts/checks/invariants.sh` and `.github/workflows/gate.yml` (rewritten below).
- The ledger rows in `docs/coderules/dependencies.md` for every package removed.

**Keep:** the `api/` toolchain (uv, ruff, `mypy --strict`, pytest, `lib/result.py`), `scripts/check-docs.sh`, `scripts/hooks/commit-msg`, `reports/`, `.env`.

**Build:**
- The `api/` skeleton from [../engine.md](../engine.md) → Layout, empty but typed.
- `api/engine/llm/openrouter.py`, ported from `api/ai/complete.py` with its three bugs fixed, the text mode, and the ledger ([../engine.md](../engine.md) → "The model seam"). `test_seam.py` comes with it.
- The gate, pre-commit only: ruff · `mypy --strict` · pytest · check-docs. The web rows return in phase 27. CI runs the same.
- `scripts/hooks/post-edit.sh` rewritten: per-file ruff and check-docs on `.md`. No full mypy, tsc or test run after every write.
- `AGENTS.md` tracked in git.
- **The bench:** 12 briefs with frozen outlines, `rubric.md`, the wall builder, and the baselines — one-shot for all 12, Gamma for 6 (the owner generates these).

### Design decisions

- **The seam is built here, not in phase 22**, because the one-shot baseline needs it and because its regression tests are cheap to write while the v3 bugs are fresh.
- **Baselines are rated before our first deck exists.** A rubric calibrated on known-bad and known-good decks is a rubric; one first used on our own output is a hope.

## Verify

- [ ] The gate is green on the skeleton
- [ ] `./scripts/check-docs.sh` passes
- [ ] Seam regression tests: invalid JSON repairs once per call with the real previous answer; a `length` finish is a typed failure; the ledger records cost
- [ ] One live smoke call under $0.05, its cost read from `usage`
- [ ] `grep -r "docs/v[123]"` finds no live pointer
- [ ] **Human:** the owner rates the one-shot, Gamma and v3 baselines on the wall

## Skipped

- CI on GitHub beyond the gate, and docker-compose — trigger: phase 29.
- `web/` — trigger: phase 27.

## Exit gate

- [ ] Gate green; docs gate green
- [ ] Baselines rated; baseline cost and time recorded in `bench/results.md`
- [ ] Prices, caching and `usage` facts recorded, dated, in `docs/techstack/ai-stack.md`
