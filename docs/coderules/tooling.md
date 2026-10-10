# Tooling

The rules above only hold if something enforces them. Three things do: a pre-commit gate, a `commit-msg` gate on what the commit *says* ([commits.md](commits.md)), and an instruction file that carries the rules into every AI session.

> **A hook that fails open is worse than no hook.** The `commit-msg` gate was written using `mapfile`, which is bash 4 and does not exist on macOS's bash 3.2. The array stayed empty, the subject read as empty, and it exited 0 on every message it was written to reject — while looking installed. Prefer `head`/`sed`/`tail` over version-dependent builtins in anything under `scripts/hooks/`, and test a new hook against a case it must **reject** before believing it works.

## The pre-commit gate

> **Rewritten 2026-09-26 for v4**, and built in phase 21 (../v4/plan/21-reset.md).

Run before a commit lands. A commit that fails any step does not land. `scripts/hooks/pre-commit` runs all of it.

```
api  (Python)                         web  (TypeScript)
1. format    — Ruff format            1. format    — Prettier
2. lint      — Ruff, no warnings      2. lint      — ESLint, no warnings
3. typecheck — mypy --strict          3. typecheck — tsc --noEmit
4. tests     — pytest (not `browser`) 4. tests     — vitest, where tests exist

both
5. OpenAPI types — regenerate web/lib/api/schema.d.ts; FAIL ON DIFF
6. docs          — scripts/check-docs.sh
```

**Step 5 replaces v3's `Deck` schema codegen check.** Pydantic is the one definition, FastAPI publishes it as OpenAPI, and `web`'s types are generated from that ([python.md](python.md)). The gate regenerates and fails on a diff, which is what makes "one source of truth" a fact across the language boundary.

Formatting stops being a decision: Prettier and Ruff own it.

**Keep the gate fast.** A gate that is fast is a gate you never `--no-verify` past. Tests that launch Chromium carry a `browser` marker and stay out of the per-commit run; CI and phase exits run them.

The lint config carries the rules that are mechanical:

| Rule | Where | Enforces |
|---|---|---|
| `@typescript-eslint/no-explicit-any` · `no-non-null-assertion` | TS | No `any`, no `!` ([typescript.md](typescript.md)) |
| Ruff `ANN` · mypy `disallow_any_explicit` | PY | Full annotations, no bare `Any` ([python.md](python.md)) |
| `import/no-internal-modules` · Ruff `TID252` + import-linter | both | Feature public-API boundary ([structure.md](structure.md)) |
| `import/no-cycle` | both | No import cycles |
| **import-linter: `engine` imports no `fastapi`, `starlette` or `features`** | PY | Engine purity ([patterns.md](patterns.md) rule 2) |
| **custom: no `os.environ` outside `settings.py`** | PY | The engine reads no environment |
| **custom: the model endpoint and `playwright` are imported only under `engine/llm/` and `engine/qa/`, `engine/export/`** | PY | One seam; one browser pool ([patterns.md](patterns.md) rule 6) |
| **custom: deck files are opened only in `api/store/files.py`** | PY | One data module ([patterns.md](patterns.md) rule 3) |
| **custom: no edit to `web/lib/api/schema.d.ts`** | TS | The codegen boundary |
| **custom: no `langchain`/`langgraph`/`crewai`/`pydantic_ai`/`autogen` in `pyproject.toml`** | PY | The agent-framework rule ([dependencies.md](dependencies.md)) |
| custom: `set_config('app.user_id'` appears in exactly **1** file | PY | Tenant isolation ([patterns.md](patterns.md) rule 4). **Added in phase 29**, with Postgres |
| `react-hooks` (incl. the compiler rules) | TS | Rules of React ([performance.md](performance.md)) |
| ~~`no-restricted-syntax` on TS `enum`~~ | | Retired — `erasableSyntaxOnly` makes it a compiler error |
| ~~no `mode` prop / `process.env` in `renderer/`~~ | | Retired 2026-09-26 — there is no TypeScript renderer |

**Retired with v3:** `scripts/checks/invariants.sh`. Much of it policed code that was deleted, and one check let through the exact defect it was written for (../findings.md). The rules above replace the parts still worth having.

CI runs the same gate plus the browser tests and the dependency-advisory check, so a bypass of the local hook is caught on push.

## What CI runs

> **2026-09-26.** v3's `.github/workflows/gate.yml` covered four packages and had never run on GitHub. Phase 21 rewrites it for two. **A workflow is unverified until it has gone green on GitHub once.**

CI mirrors the gate and adds what is too slow or needs a browser:

| | |
|---|---|
| **The gate** | Exactly the six steps above, for `api` and `web` |
| **Browser tests** | The `browser`-marked pytest suite: the offline `file://` zero-request test, the QA-metric fixtures, PDF |
| **Advisories** | `pnpm audit` at critical in `web`; `pip-audit` over the exported uv lockfile |
| **Duplication** | jscpd on changed files, `continue-on-error` — a signal, not a gate ([ai-authorship.md](ai-authorship.md)) |
| **`next build`** | From phase 27. The only check that compiles every route |
| **Deploy** | Phase 29 |

**CI never runs the bench.** It costs model credits.

## Evals are the bench, and the wall gates phases

The pipeline's quality has no type system behind it. v3 tried to gate it in CI with a variety check that ran on a stub model, and it passed on decks that looked bad. v4 splits it differently ([../v4/bench.md](../v4/bench.md)):

| | Runs | Gates? |
|---|---|---|
| **Structural checks** — sanitizer, lint, QA-metric fixtures, the offline test, the seam's repair path | Every commit / CI | **Yes. Hard fail on a merge** |
| **The bench** — real model calls on the briefs in repo-root `bench/`, content evals, cost and time per deck | The 3-deck smoke set during a phase; all 12 at a phase exit | **Not a merge gate** |
| **The human wall** — the owner scores every bench deck 1–5 | Every phase exit | **Gates the phase exit, never a merge** |

**A probabilistic judge must never block a merge.** It will fail on a good change eventually, and the first override turns the gate into decoration. **A phase, though, does not close on green checks alone**: automated gates cannot see design (../findings.md → Process).

**Prompts are code.** They live in the repo as versioned files, and a prompt change is a behaviour change with a bench result attached ([../techstack/ai-stack.md](../techstack/ai-stack.md)).

## Some of the custom rules may already exist

`eslint-plugin-import-boundaries` implements exactly the model in [structure.md](structure.md): a boundary's `index.ts` *is* its public surface, and everything else in the folder is private to it. If it fits, the feature-boundary rule stops being custom code and becomes a config block. `eslint-plugin-boundaries` and `dependency-cruiser` cover the same ground with more configuration and more power than this project needs.

Check before writing the custom rule. A rule you did not write is a rule you do not maintain — and the genuinely project-specific ones, above all the tenant-wrapper rule, are worth your attention precisely because nothing off the shelf knows this codebase's invariants.

## Which linter and formatter

The Rust-based tools are now genuinely competitive, and for a greenfield project this is a real choice rather than a novelty.

| | |
|---|---|
| **Biome v2** | Lint *and* format in one binary, 50–100× faster than ESLint, type-aware rules, no Prettier needed |
| **Oxlint** | Lint only, fastest of the three (8.6s vs ESLint's 54s on one real codebase), type-aware via `tsgo`, covers 59 of 61 `@typescript-eslint` type-aware rules. Its March 2026 JS-plugin alpha runs most ESLint plugins unmodified |
| **ESLint + Prettier** | Slowest, unmatched plugin ecosystem, and the only one where every Next.js and React rule is guaranteed to exist today |

**Stay on ESLint + Prettier for now.** Not because it is better — it is slower and it is two tools where Biome is one — but because this project's `web` gate leans on the import-boundary rule and on the React and Next.js plugin sets, and "the plugin exists" is worth more than "the linter is fast" on a codebase that will not be large enough for the speed to be felt.

The condition for revisiting is concrete: **when the custom rules can be expressed in Biome, switch.** That trades two tools for one and deletes the Prettier config, which is the kind of subtraction this project favours. Speed is not the reason; one binary instead of two is.

There is a genuine middle option if the gate ever feels slow: run Oxlint as a fast pre-check in the hook and keep ESLint in CI. Do not do this preemptively — it is two linters instead of one to save time nobody has yet lost.

## Tests

**pytest** in `api`; **Vitest** in `web`, plus Playwright for the app's end-to-end flow from phase 27.

What gets tested is deliberately narrow ([ai-authorship.md](ai-authorship.md)); the list is in [python.md](python.md) → "Test". Slide quality is a human judgment and gets the wall, not a snapshot. A snapshot test on a design surface fails on every intentional improvement and teaches you to update it without looking.

## What is NOT gated

No coverage threshold. No mandated JSDoc. No lint rule for comment density. These measure the wrong thing and punish good judgment — the ponytail rule on tests (one runnable check per non-trivial branch, none for trivial code) is a judgment call a coverage number would override with busywork.

## The instruction file — rules into every AI session

Most of this codebase is written by Claude. The cheapest consistency win available is an instruction file that states the non-negotiables inline and points at this directory for the rest. Every session inherits them without being re-told; drift never gets a chance to start.

**`AGENTS.md` holds the rules; `CLAUDE.md` imports it.** `AGENTS.md` is the cross-tool standard — stewarded by the Agentic AI Foundation under the Linux Foundation, read natively by Codex, Cursor, Copilot, Gemini CLI, Aider, Windsurf, and Zed. Claude Code reads `CLAUDE.md` and not `AGENTS.md`, and Anthropic's own guidance for a repo with both is to have `CLAUDE.md` import `AGENTS.md`. That gives one source of truth and keeps the project portable if the tool changes — the same rule as everywhere else here, applied to the rules themselves.

The file is derived from this directory, which stays the source. When a rule changes here, it changes there.

**Both files exist at the repo root — read them rather than a copy.** `AGENTS.md` carries the eleven non-negotiables from the [README](README.md) (rewritten to one page in phase 21), a task-to-document routing table, and the short list of things never to do. `CLAUDE.md` is one line: `@AGENTS.md`. Reproducing either here would create a second source of truth for the rules whose entire point is that there is one.

### Three mechanics that decide whether this works

**`@` imports are eager, not lazy.** Claude Code expands `@path` inline at session start, so imported content costs tokens on every turn of every session. It does **not** reduce context — it exists for portability. The consequence is the one thing most likely to be "improved" wrongly:

> **Never `@`-import this directory into `AGENTS.md`.** That would inline ~900 lines into every session, including the ones that never touch code. The docs are referenced by **plain path**, so they are read only when the task actually needs them.

**Keep the instruction file short and stable.** It loads before Claude sees any code, so it is a constant tax. The working guidance is an index under ~50 lines: non-negotiables plus pointers, not documentation. And every edit invalidates the prompt cache and forces a full re-process — so batch changes rather than tweaking between sessions.

**Rules in an instruction file are advisory; hooks are enforcement.** This is the important one, and it is why the section below exists. A rule in `AGENTS.md` asks the model to remember. Remembering is not enforcement, and it degrades across long sessions and context compaction. A hook runs every time, regardless of how the request was phrased.

## Hooks — project level, never global

`.claude/settings.json` is committed; `.claude/settings.local.json` is personal and stays ignored. Nothing belongs in `~/.claude/`, because a rule that lives on one machine is not a project rule.

```jsonc
// .claude/settings.json
"hooks": { "PostToolUse": [{ "matcher": "Edit|Write",
  "hooks": [{ "type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR/scripts/hooks/post-edit.sh\"" }] }] }
```

`scripts/hooks/post-edit.sh` reads the tool payload and checks **the file that was just written**. Exit 2 sends the output back to the agent, so it fixes the file while it still remembers why it wrote the line.

**Rewritten in phase 21 (2026-09-26), not deleted.** The v3 hook ran full `mypy`, full `tsc` and the invariants script after every write, and any `web/src` change launched Chromium. That is a gate's job done at the wrong moment. The rule now:

| The hook runs, per file | Moved to pre-commit |
|---|---|
| `*.py` → `ruff check` + `ruff format --check` on that file | `mypy --strict` |
| `*.ts`/`*.tsx` → `eslint` on that file | `tsc --noEmit` |
| `*.md` → `scripts/check-docs.sh` | `pytest`, the OpenAPI no-diff step |

Whole-project checks belong to the pre-commit gate; the hook only moves the cheap, per-file feedback earlier.

The gate catches mechanics; the instruction file carries the architecture and naming intent a linter cannot express.

## Setup cost

All of this is a few hours, once, in phase 21: `pyproject.toml` (ruff, mypy, pytest, import-linter), `tsconfig`, an ESLint config, Prettier, the hooks under `scripts/hooks/` installed by `scripts/setup.sh`, `pnpm` and `uv` with their safe defaults, and an `AGENTS.md`. It is the cheapest insurance in the project: it makes the consistent thing the *easy* thing.
