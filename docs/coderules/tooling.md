# Tooling

The rules above only hold if something enforces them. Two things do: a pre-commit gate, and an instruction file that carries the rules into every AI session.

## The pre-commit gate

`husky` + `lint-staged` run on staged files before a commit lands. A commit that fails any step does not land.

```
1. format   — Prettier, fixes in place
2. lint     — ESLint, no warnings allowed on changed files
3. typecheck — tsc --noEmit
```

Formatting stops being a decision — Prettier owns it, there is nothing to discuss and nothing to be inconsistent about. The whole point is to move consistency out of your head and into a hook that cannot be forgotten under deadline pressure.

**Keep the gate under a couple of seconds, and treat that as a requirement rather than a nicety.** A gate that is fast is a gate you never `--no-verify` past, and every rule in this directory is only as real as the hook that runs it. Step 3 is the one that grows: `tsc --noEmit` is the slowest step and the one that scales with the codebase. If it ever becomes the reason you skip the hook, that is the signal to move to the Go-native compiler ([typescript.md](typescript.md)) — 8–12× is enough headroom to never think about this again.

The lint config carries the rules that are mechanical:

| Rule | Enforces |
|---|---|
| `@typescript-eslint/no-explicit-any` | No `any` ([typescript.md](typescript.md)) |
| `no-non-null-assertion` | No `!` |
| `import/no-internal-modules` (feature-scoped) | Feature public-API boundary ([structure.md](structure.md)) |
| `import/no-cycle` | No import cycles |
| custom: no `mode` prop in `renderer/` | Renderer core stays pure ([patterns.md](patterns.md)) |
| custom: no Drizzle import outside `*.data.ts` | Data access stays in feature modules |
| custom: no `db.` call outside the `asUser` wrapper | Tenant isolation ([patterns.md](patterns.md) rule 4) — the highest-value custom rule in the list |
| custom: no `process.env` / `typeof window` in `renderer/` | The renderer runs in three processes and must behave identically in all of them |
| `react-hooks` (incl. the compiler rules) | Rules of React — a violation silently costs you React Compiler memoization ([performance.md](performance.md)) |
| ~~`no-restricted-syntax` on TS `enum`~~ | Retired — `erasableSyntaxOnly` makes it a compiler error ([typescript.md](typescript.md)) |

The custom rules are worth the small effort to write — they are exactly the project-specific invariants prose cannot enforce, and each maps to a decision that quietly unravels the product if it drifts. The `asUser` rule is the one to write first: it is the only one on the list whose violation is a cross-tenant read rather than a design regression.

CI runs the same gate plus the test suites and the dependency-advisory check, so a bypass of the local hook is caught on push.

## What CI runs, across two repos

The gate above is per-commit and fast. CI adds the things that are too slow or need a browser, and it now spans two repos and three deploy targets ([../techstack/infrastructure.md](../techstack/infrastructure.md)).

| | |
|---|---|
| **Both repos** | The gate · Vitest · dependency advisories · duplication report ([ai-authorship.md](ai-authorship.md)) |
| **App repo** | Playwright — sandbox escape, the two-requests `connect-src` assertion, cross-origin behavior · build-output grep for key-shaped strings · Promptfoo structural evals |
| **Fetch worker repo** | SSRF suite including socket-level unreachability — a test of the network, not the code |
| **Terraform** | `plan` on PR, `apply` on merge. A security-group change should be at least as visible as an auth-check change, since nothing type-checks it |
| **Docs** | `scripts/check-docs.sh` — every relative link resolves, every `.md` is listed in its directory's README, every directory has one |

That last row is small and it is the only thing that keeps the navigation in [../README.md](../README.md) true. An index that silently stops listing a file is worse than no index, because it teaches a reader — or an agent — that the directory contains less than it does. The check takes a second and fails on both the dead link and the unlisted file.
| **Deploy** | Vercel on push; worker images to ECR via OIDC — no long-lived AWS keys in GitHub |

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

Check before writing the custom rule. A rule you did not write is a rule you do not maintain — and the genuinely project-specific ones, above all the `asUser` ban, are worth your attention precisely because nothing off the shelf knows this codebase's invariants.

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

**Vitest.** `node:test` is stdlib and faster on raw unit throughput, which normally settles it — but it has no watch mode, no snapshots, and no real React Testing Library story, and this project's tests are mostly renderer and component tests. Rung 3 of the ladder says use the stdlib; rung 3 also says use it when it *does the job*, and here it does not.

What gets tested is unchanged and deliberately narrow ([ai-authorship.md](ai-authorship.md), [../v1/spec.md](../v1/spec.md)): the schema round-trip, the golden-brief pipeline run, the block patch, the no-styling backstop, the AD linter. Renderer quality is a human judgment and gets a visual check, not a snapshot — a snapshot test on a design surface fails on every intentional improvement and teaches you to update it without looking.

## What is NOT gated

No coverage threshold. No mandated JSDoc. No lint rule for comment density. These measure the wrong thing and punish good judgment — the ponytail rule on tests (one runnable check per non-trivial branch, none for trivial code) is a judgment call a coverage number would override with busywork.

## The instruction file — rules into every AI session

Most of this codebase is written by Claude. The cheapest consistency win available is an instruction file that states the non-negotiables inline and points at this directory for the rest. Every session inherits them without being re-told; drift never gets a chance to start.

**`AGENTS.md` holds the rules; `CLAUDE.md` imports it.** `AGENTS.md` is the cross-tool standard — stewarded by the Agentic AI Foundation under the Linux Foundation, read natively by Codex, Cursor, Copilot, Gemini CLI, Aider, Windsurf, and Zed. Claude Code reads `CLAUDE.md` and not `AGENTS.md`, and Anthropic's own guidance for a repo with both is to have `CLAUDE.md` import `AGENTS.md`. That gives one source of truth and keeps the project portable if the tool changes — the same rule as everywhere else here, applied to the rules themselves.

The file is derived from this directory, which stays the source. When a rule changes here, it changes there. It stays short: the eleven non-negotiables from the [README](README.md), plus pointers.

```markdown
# AGENTS.md

Read docs/coderules/ before writing code. Non-negotiable:

1. Strict TS. No `any`, no `!`.
2. One Zod parse per external input, at entry. Model output, tool-call
   arguments, and Server Action inputs are all external input.
3. Expected failures return Result; only bugs throw.
4. Import across features only through their index.ts.
5. No new dependency without a ledger line in docs/coderules/dependencies.md.
   Anything parsing untrusted bytes goes in the fetch worker.
6. renderer/ core is pure — no mode prop, no mode branches, no process.env,
   no typeof window. It runs in three processes and must behave identically.
7. AI output carries no presentational values (hex/px/font/duration).
8. Drizzle only in *.data.ts inside a feature, and those files are
   `import 'server-only'`.
9. Every tenant-scoped query goes through the asUser() transaction wrapper.
   A db call outside it is a cross-tenant read waiting to happen.
10. Anything that grants, fails closed. A catch returning a permissive
    default is a vulnerability, not error handling.
11. Pre-commit gate (typecheck, lint, format) must be green.

Before writing a helper, grep for it. This codebase's most likely defect is a
second copy of something that already exists, not a bug.

Build in ponytail mode: laziest solution that works. Prefer platform over
dependency, one line over fifty, deletion over addition. Mark cut corners
with a `ponytail:` comment naming the ceiling.
```

```markdown
# CLAUDE.md

@AGENTS.md
```

The tenth line is not one of the nine, and it is there because of what the data in [ai-authorship.md](ai-authorship.md) says: duplication, not incorrectness, is what degrades an AI-written codebase, and it is the one failure the gate cannot catch. Rules 1–9 are things a linter could theoretically enforce. That line is the one that has to be said, because nothing else will say it.

The gate catches mechanics; the instruction file carries the architecture and naming intent a linter cannot express. Together they cover both — objective rules by the machine, judgment rules by the primed author.

## Setup cost

All of this is a few hours, once: `tsconfig`, an ESLint config with a handful of custom rules, Prettier, a husky hook, `pnpm` with its defaults left alone, and an `AGENTS.md`. It is the cheapest insurance in the project — it makes the consistent thing the *easy* thing, which is the only way consistency survives a solo build with an AI pair.
