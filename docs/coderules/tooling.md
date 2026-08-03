# Tooling

The rules above only hold if something enforces them. Two things do: a pre-commit gate, and a `CLAUDE.md` that carries the rules into every AI session.

## The pre-commit gate

`husky` + `lint-staged` run on staged files before a commit lands. A commit that fails any step does not land.

```
1. format   — Prettier, fixes in place
2. lint     — ESLint, no warnings allowed on changed files
3. typecheck — tsc --noEmit
```

Formatting stops being a decision — Prettier owns it, there is nothing to discuss and nothing to be inconsistent about. The whole point is to move consistency out of your head and into a hook that cannot be forgotten under deadline pressure.

The lint config carries the rules that are mechanical:

| Rule | Enforces |
|---|---|
| `@typescript-eslint/no-explicit-any` | No `any` ([typescript.md](typescript.md)) |
| `no-non-null-assertion` | No `!` |
| `import/no-internal-modules` (feature-scoped) | Feature public-API boundary ([structure.md](structure.md)) |
| `import/no-cycle` | No import cycles |
| custom: no `mode` prop in `renderer/` | Renderer core stays pure ([patterns.md](patterns.md)) |
| custom: no Drizzle import outside `*.data.ts` | Data access stays in feature modules |
| `no-restricted-syntax` on TS `enum` | Const objects over enums |

The three custom rules are worth the small effort to write — they are exactly the project-specific invariants prose cannot enforce, and each maps to a decision that quietly unravels the product if it drifts.

CI runs the same gate plus the test suites and the dependency-advisory check, so a bypass of the local hook is caught on push.

## What is NOT gated

No coverage threshold. No mandated JSDoc. No lint rule for comment density. These measure the wrong thing and punish good judgment — the ponytail rule on tests (one runnable check per non-trivial branch, none for trivial code) is a judgment call a coverage number would override with busywork.

## CLAUDE.md — rules into every AI session

Most of this codebase is written by Claude. The cheapest consistency win available is a repo `CLAUDE.md` that states the non-negotiables inline and points at this directory for the rest. Every session inherits them without being re-told; drift never gets a chance to start.

`CLAUDE.md` is derived from these rules — this directory is the source, `CLAUDE.md` is the enforcement surface. When a rule changes here, `CLAUDE.md` changes with it. It stays short: the nine non-negotiables from the [README](README.md), plus pointers.

```markdown
# CLAUDE.md

Read docs/coderules/ before writing code. Non-negotiable:

1. Strict TS. No `any`, no `!`.
2. One Zod parse per external input, at entry. AI output is untrusted input.
3. Expected failures return Result; only bugs throw.
4. Import across features only through their index.ts.
5. No new dependency without a ledger line in docs/coderules/dependencies.md.
6. renderer/ core is pure — no mode prop, no mode branches.
7. AI output carries no presentational values (hex/px/font/duration).
8. Drizzle only in *.data.ts inside a feature.
9. Pre-commit gate (typecheck, lint, format) must be green.

Build in ponytail mode: laziest solution that works. Prefer platform over
dependency, one line over fifty, deletion over addition. Mark cut corners
with a `ponytail:` comment naming the ceiling.
```

The gate catches mechanics; `CLAUDE.md` carries the architecture and naming intent a linter cannot express. Together they cover both — objective rules by the machine, judgment rules by the primed author.

## Setup cost

All of this is a few hours, once: `tsconfig`, an ESLint config with three custom rules, Prettier, a husky hook, and a `CLAUDE.md`. It is the cheapest insurance in the project — it makes the consistent thing the *easy* thing, which is the only way consistency survives a solo build with an AI pair.
