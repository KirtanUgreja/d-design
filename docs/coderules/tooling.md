# Tooling

The rules above only hold if something enforces them. Three things do: a pre-commit gate, a `commit-msg` gate on what the commit *says* ([commits.md](commits.md)), and an instruction file that carries the rules into every AI session.

> **A hook that fails open is worse than no hook.** The `commit-msg` gate was written using `mapfile`, which is bash 4 and does not exist on macOS's bash 3.2. The array stayed empty, the subject read as empty, and it exited 0 on every message it was written to reject — while looking installed. Prefer `head`/`sed`/`tail` over version-dependent builtins in anything under `scripts/hooks/`, and test a new hook against a case it must **reject** before believing it works.

## The pre-commit gate

Run on staged files before a commit lands. A commit that fails any step does not land. **The steps differ per repo because the languages do; the discipline does not.**

```
TypeScript repos  (husky + lint-staged)   Python repo  (pre-commit)
1. format    — Prettier                   1. format    — Ruff format
2. lint      — ESLint, no warnings        2. lint      — Ruff, no warnings
3. typecheck — tsc --noEmit               3. typecheck — mypy --strict
                                          4. schema    — regenerate; FAIL ON DIFF
```

**Step 4 is the one that did not exist before and is the most important thing on this page.** The `Scene` schema lives in Pydantic and TypeScript consumes a generated copy ([python.md](python.md)). If the generated output can drift from its source, the single-source rule is a comment rather than a fact. The gate regenerates and fails if the result differs from what is committed — which makes "one source of truth" true by construction across a language boundary, the same way `z.infer` used to make it true within one.

Formatting stops being a decision — Prettier and Ruff own it, there is nothing to discuss and nothing to be inconsistent about. The whole point is to move consistency out of your head and into a hook that cannot be forgotten under deadline pressure.

**Keep the gate under a couple of seconds, and treat that as a requirement rather than a nicety.** A gate that is fast is a gate you never `--no-verify` past, and every rule in this directory is only as real as the hook that runs it. Step 3 is the one that grows: `tsc --noEmit` is the slowest step and the one that scales with the codebase. If it ever becomes the reason you skip the hook, that is the signal to move to the Go-native compiler ([typescript.md](typescript.md)) — 8–12× is enough headroom to never think about this again.

The lint config carries the rules that are mechanical:

| Rule | Where | Enforces |
|---|---|---|
| `@typescript-eslint/no-explicit-any` · `no-non-null-assertion` | TS | No `any`, no `!` ([typescript.md](typescript.md)) |
| Ruff `ANN` · mypy `disallow_any_explicit` | PY | Full annotations, no bare `Any` ([python.md](python.md)) |
| `import/no-internal-modules` · Ruff `TID252` + import-linter | both | Feature public-API boundary ([structure.md](structure.md)) |
| `import/no-cycle` | both | No import cycles |
| custom: no `mode` prop in `renderer/` | TS | Renderer core stays pure ([patterns.md](patterns.md)) |
| custom: no `process.env` / `typeof window` in `renderer/` | TS | The renderer runs in three processes and must behave identically in all of them |
| custom: no ORM import outside a data module | both | Data access stays in feature modules ([patterns.md](patterns.md) rule 3) |
| **custom: `set_config('app.user_id'` appears in exactly *N* files** | both | Tenant isolation ([patterns.md](patterns.md) rule 4). **The highest-value rule in the list** — it is what turns "exactly two wrappers" from a claim into a fact. `N` is a literal: **1 through v2, 2 from v3** when Better Auth arrives. Raising it is a deliberate edit to a rule, never a silent widening |
| **custom: no edit to generated `@d-design/schema` sources** | TS | The codegen boundary. A hand-edit is the only remaining door for schema drift |
| **custom: no `langchain`/`langgraph`/`crewai`/`pydantic_ai`/`autogen` in `pyproject.toml`** | PY | The agent-framework rule ([dependencies.md](dependencies.md)) — a privileged dependency does not arrive by accident |
| **custom: Alembic `include_object` excludes the auth tables** | PY | Two migration tools, one database. Without it, autogenerate proposes dropping seven tables it does not know about |
| `react-hooks` (incl. the compiler rules) | TS | Rules of React — a violation silently costs you React Compiler memoization ([performance.md](performance.md)) |
| ~~`no-restricted-syntax` on TS `enum`~~ | | Retired — `erasableSyntaxOnly` makes it a compiler error ([typescript.md](typescript.md)) |

The custom rules are worth the small effort to write — they are exactly the project-specific invariants prose cannot enforce, and each maps to a decision that quietly unravels the product if it drifts.

**Four of them are new, and all four exist because the Python move replaced a structural guarantee with a procedural one.** There used to be one language, so there was one tenant wrapper, one schema, and no way to install LangGraph without also installing Python. None of that is true now, and each bolded rule above is the gate standing in for a barrier that used to be free ([../techstack/decisions.md](../techstack/decisions.md) → "The Python backend move"). Write the `set_config` rule first: it is the only one whose violation is a cross-tenant read rather than a design regression.

CI runs the same gate plus the test suites and the dependency-advisory check, so a bypass of the local hook is caught on push.

## What CI runs, across five repos

> **No CI exists right now.** The workflow was deleted on 2026-08-10 with the codebase — it ran the gate against `api/` and `web/`, neither of which is here. This section is the specification for what to rebuild, not a description of what runs. The local hook in `scripts/hooks/pre-commit` is the only gate today, which means a bypass of it is currently caught by nothing.

The gate above is per-commit and fast. CI adds the things that are too slow or need a browser, and it now spans five repos ([../techstack/infrastructure.md](../techstack/infrastructure.md)).

| | |
|---|---|
| **Every repo** | The gate · tests · dependency advisories · duplication report ([ai-authorship.md](ai-authorship.md)) |
| **`api`** | pytest · **schema regenerates with no diff** · **the cross-language fixture round-trip** ([python.md](python.md)) · Promptfoo structural evals · injection corpus · the fail-closed suite (make each check raise, assert refusal) |
| **`web`** | Playwright — sandbox escape, the two-requests `connect-src` assertion, cross-origin behaviour · build-output grep for key-shaped strings |
| **`render`** | Renders every primitive under every art direction and diffs nothing — it is a visual check with a human, not a snapshot suite |
| **fetch worker** | SSRF suite including socket-level unreachability — a test of the network, not the code |
| **Schema publish** | On merge to `api`: generate, version-bump, publish `@d-design/schema` via OIDC. **Consumers are bumped in the same session** ([typescript.md](typescript.md)) |
| **Terraform** | `plan` on PR, `apply` on merge. A security-group change should be at least as visible as an auth-check change, since nothing type-checks it |
| **Docs** | `scripts/check-docs.sh` — every relative link resolves, every `.md` is listed in its directory's README, every directory has one |
| **Deploy** | Vercel on push for `web`; container images to ECR via OIDC for the rest — no long-lived AWS keys in GitHub |

**Five repos is the largest ongoing cost of the split**, and it is felt here rather than in the architecture diagram: a schema change is now a generate, a publish, and up to three bumps. During v1 there is one TypeScript consumer and a local file link is the right shortcut — marked `ponytail:`, with `render`'s arrival in v2 as the trigger to do it properly.

The docs row is small and it is the only thing keeping the navigation in [../README.md](../README.md) true. An index that silently stops listing a file is worse than no index, because it teaches a reader — or an agent — that the directory contains less than it does.

## Evals are two things, and only one of them gates

The pipeline's quality has no type system behind it, so it needs its own gate — but treating all of it the same way is how the gate stops being trusted.

| | Runs | Gates? |
|---|---|---|
| **Structural evals** — valid `Scene` JSON, no presentational values, every `CTA.href` from the Brief, budgets respected, the injection corpus | Every PR | **Yes. Hard fail** |
| **Quality scoring** — layout variety, copy fidelity, motion appropriateness | Nightly | **No. Tracked as a trend** |

**A probabilistic judge must never block a merge.** It will fail on a good change eventually, and the first time someone overrides it to ship, the gate is decoration. Watch the trend and investigate a drop instead. This is the same split the injection suite already uses — structural assertions absolute, model-dependent ones measured as a rate ([../security/testing.md](../security/testing.md)).

**Prompts are code.** They live in the repo, move through the same review, and a prompt change is a behavior change with eval results attached ([../techstack/ai-stack.md](../techstack/ai-stack.md)). A prompt edited in a database is a production change with no diff.

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

**Stay on ESLint + Prettier for now.** Not because it is better — it is slower and it is two tools where Biome is one — but because this project's gate leans on several custom rules and on the React and Next.js plugin sets, and "the plugin exists" is worth more than "the linter is fast" on a codebase that will not be large enough for the speed to be felt.

The condition for revisiting is concrete: **when the custom rules can be expressed in Biome, switch.** That trades two tools for one and deletes the Prettier config, which is the kind of subtraction this project favours. Speed is not the reason; one binary instead of two is.

There is a genuine middle option if the gate ever feels slow: run Oxlint as a fast pre-check in the hook and keep ESLint in CI. Do not do this preemptively — it is two linters instead of one to save time nobody has yet lost.

## Tests

**pytest** in `api`; **Vitest** in the TypeScript repos. `node:test` is stdlib and faster on raw unit throughput, which normally settles it — but it has no watch mode, no snapshots, and no real React Testing Library story, and the TypeScript tests are mostly renderer and component tests. Rung 3 of the ladder says use the stdlib; rung 3 also says use it when it *does the job*, and here it does not.

What gets tested is unchanged and deliberately narrow ([ai-authorship.md](ai-authorship.md), `v1/spec.md`): the schema round-trip, the golden-brief pipeline run, the block patch, the no-styling backstop, the AD linter — **plus the two the language split added**, the codegen no-diff check and the cross-language fixture round-trip ([python.md](python.md)). Renderer quality is a human judgment and gets a visual check, not a snapshot — a snapshot test on a design surface fails on every intentional improvement and teaches you to update it without looking.

## What is NOT gated

No coverage threshold. No mandated JSDoc. No lint rule for comment density. These measure the wrong thing and punish good judgment — the ponytail rule on tests (one runnable check per non-trivial branch, none for trivial code) is a judgment call a coverage number would override with busywork.

## The instruction file — rules into every AI session

Most of this codebase is written by Claude. The cheapest consistency win available is an instruction file that states the non-negotiables inline and points at this directory for the rest. Every session inherits them without being re-told; drift never gets a chance to start.

**`AGENTS.md` holds the rules; `CLAUDE.md` imports it.** `AGENTS.md` is the cross-tool standard — stewarded by the Agentic AI Foundation under the Linux Foundation, read natively by Codex, Cursor, Copilot, Gemini CLI, Aider, Windsurf, and Zed. Claude Code reads `CLAUDE.md` and not `AGENTS.md`, and Anthropic's own guidance for a repo with both is to have `CLAUDE.md` import `AGENTS.md`. That gives one source of truth and keeps the project portable if the tool changes — the same rule as everywhere else here, applied to the rules themselves.

The file is derived from this directory, which stays the source. When a rule changes here, it changes there.

**Both files exist at the repo root — read them rather than a copy.** `AGENTS.md` carries the eleven non-negotiables from the [README](README.md), a task-to-document routing table, and the short list of things never to do. `CLAUDE.md` is one line: `@AGENTS.md`. Reproducing either here would create a second source of truth for the rules whose entire point is that there is one.

### Three mechanics that decide whether this works

**`@` imports are eager, not lazy.** Claude Code expands `@path` inline at session start, so imported content costs tokens on every turn of every session. It does **not** reduce context — it exists for portability. The consequence is the one thing most likely to be "improved" wrongly:

> **Never `@`-import this directory into `AGENTS.md`.** That would inline ~900 lines into every session, including the ones that never touch code. The docs are referenced by **plain path**, so they are read only when the task actually needs them.

**Keep the instruction file short and stable.** It loads before Claude sees any code, so it is a constant tax. The working guidance is an index under ~50 lines: non-negotiables plus pointers, not documentation. And every edit invalidates the prompt cache and forces a full re-process — so batch changes rather than tweaking between sessions.

**Rules in an instruction file are advisory; hooks are enforcement.** This is the important one, and it is why the section below exists. A rule in `AGENTS.md` asks the model to remember. Remembering is not enforcement, and it degrades across long sessions and context compaction. A hook runs every time, regardless of how the request was phrased.

## Hooks — project level, never global

`.claude/settings.json` is committed; `.claude/settings.local.json` is personal and stays ignored. Everything is scoped to this repo — nothing belongs in `~/.claude/`, because a rule that lives on one machine is not a project rule.

```jsonc
// .claude/settings.json
"hooks": { "PostToolUse": [{ "matcher": "Edit|Write",
  "hooks": [{ "type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR/scripts/hooks/post-edit.sh\"" }] }] }
```

`scripts/hooks/post-edit.sh` reads the tool payload, looks at what was written, and runs the checks that apply to it. Exit 2 sends the output back to the agent, so it fixes the file it just wrote rather than discovering the problem at commit time.

Today it enforces one thing — `.md` edits must keep `scripts/check-docs.sh` passing. **Add a line per rule as the code that needs it appears**, and prefer the rules whose violation is silent:

| Add when | Enforces |
|---|---|
| `*.ts` exists | `tsc --noEmit` and `eslint` on the written file — rule 11, at write time instead of commit time |
| `*.py` exists | `mypy` and `ruff` on the written file — the same rule, the other language |
| **`api/schema/` exists** | Regenerate and fail on diff. **Add this the day the schema does**, not later — it is the rule most likely to be violated invisibly by an agent editing generated TypeScript because it looked wrong |
| A data module exists | Rules 8 and 9 — the ORM placement and the tenant wrapper |
| The renderer exists | Rule 6 — no `process.env` or `typeof window` under `renderer/` |

The pre-commit gate still runs all of it; the hook just moves the feedback earlier, to the moment the agent can still remember why it wrote the line.

The gate catches mechanics; the instruction file carries the architecture and naming intent a linter cannot express. Together they cover both — objective rules by the machine, judgment rules by the primed author.

## Setup cost

All of this is a few hours, once: `tsconfig`, an ESLint config with a handful of custom rules, Prettier, a husky hook, `pnpm` with its defaults left alone, and an `AGENTS.md`. It is the cheapest insurance in the project — it makes the consistent thing the *easy* thing, which is the only way consistency survives a solo build with an AI pair.
