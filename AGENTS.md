# d-design

> **Sprint to submission: `docs/v4/plan/master-plan.md`** — build day 2026-10-09 (no model credit), test day 2026-10-10, submit by 2026-10-10. Read it first.
>
> **The plan is `docs/v4/`, decided 2026-09-26.** Status is in `docs/v4/plan/README.md`. The v3 code is gone (tag `v3-final`); `api/` holds the v4 engine skeleton and `web/` returns in phase 27.

## What the product is

An AI presentation maker whose edge over Gamma is **design**. A founder or salesperson types a brief and gets a deck that looks designed and says something, exported as **one offline `.html` file** with zero network requests.

- **The model composes each slide in real HTML and CSS**, inside a per-deck design system. Colour and type come only from theme tokens; layout is free.
- **Every slide is rendered in Chromium and measured** before a user sees it. Defects are repaired, or the slide is flagged.
- **Every number traces to the user or a cited source**, or is flagged.
- **Python backend (FastAPI) owns the engine, data and export. The Next.js frontend is UI only.**

**Reversed on 2026-09-26:** "the AI never writes styling". It capped the output at five visual variables (`docs/findings.md` → "Measured 2026-09-26").

## Commands that work today

```
./scripts/setup.sh               installs the git hooks — run once per clone
./scripts/check-docs.sh          every link resolves, every file is indexed
./scripts/hooks/pre-commit       the gate, on demand

cd api
uv run pytest -q                           the tests
uv run python -m cli smoke                 one live model call; prints its cost
uv run python -m cli freeze --set all      freeze outlines for the bench briefs
uv run python -m cli baseline --set all    one-shot baseline decks + screenshots
uv run python -m cli wall --run NAME       the wall page the owner scores
uv run python -m cli sameness              coverage and repeat rate (phase 36)
uv run uvicorn app:serve --factory --port 8000 the API (enqueues and reads; never calls a model)
uv run python worker.py                    the worker (holds the key; builds decks)
```

`.env` holds `OPENROUTER_API_KEY`. It is gitignored.

## Read before you write

Paths are **pointers, not imports** — read the file when the task touches it. Never prefix with `@`.

| Task touches | Read first |
|---|---|
| **What to build next** | `docs/v4/plan/README.md`, then the phase file |
| Why a decision was made | `docs/v4/spec.md` |
| Where a module goes, the data model, events, the model seam | `docs/v4/engine.md` |
| Slide HTML, the lint, QA metrics, themes, exemplars | `docs/v4/design-engine.md` |
| Copy, the interview, facts, storylines | `docs/v4/content.md` |
| Running the bench, scoring the wall, budgets | `docs/v4/bench.md` |
| Any code at all | `docs/coderules/README.md` |
| Adding a package — **including any agent framework** | `docs/coderules/dependencies.md` |
| User input, model-written HTML, CSP, tokens | `docs/security/README.md` |
| Models, prompts, caching, web search | `docs/techstack/ai-stack.md` |
| Our own app's screens and look | `docs/design/app.md`, `docs/design/brand.md` |
| "Do we already know this?" | `docs/findings.md` |

## The non-negotiables

Full text and reasons: `docs/coderules/README.md`.

1. Strict types both sides. TS: no `any`, no `!`. Python: `mypy --strict`.
2. One schema parse per external input, at entry. Model output is external input: slide HTML is sanitized and linted at entry.
3. Expected failures return `Result`; only bugs raise.
4. Import across features only through their public surface.
5. No new dependency without a ledger line. An agent framework needs one too.
6. The engine is pure: `api/engine/` imports no web framework and reads no environment.
7. **Model output may reference only theme tokens for colour and type.** No gradients, blur, glow, links, icons or animation in slides.
8. Data access lives in one Python data module. The web app has no database — except Better Auth's own tables in the `auth` database (owner, 2026-10-08), which Python never reads.
9. One tenant wrapper, in Python, from phase 29.
10. Anything that grants, fails closed — including the budget cap and QA ("a failure to measure is an error").
11. The gate is green, or the commit does not land.

## How to work

- **A phase is not done until the owner has scored the wall** (`docs/v4/bench.md`). Automated gates cannot see design.
- **Before writing a helper, grep for it.** The measured failure of AI-written code is duplication.
- **Ponytail mode:** the laziest solution that works. Mark a deliberate shortcut with a `ponytail:` comment naming the ceiling and the upgrade path.
- **Never:** give the model a tool with side effects · log prompts or deck content · hand-edit generated code · install an agent framework · spend bench credits on the full set between phase exits.
- **Commits:** subject ≤72 chars, no trailing period; a body saying what was wrong and what the project can do now; one block per file. **No `Co-Authored-By`, no tool attribution** — `scripts/hooks/commit-msg` rejects them. Rule: `docs/coderules/commits.md`.
- **Branches:** `phase-21-reset` … `phase-29-accounts-deploy`.
- **Docs:** editing any `.md` means `./scripts/check-docs.sh` must still pass.
