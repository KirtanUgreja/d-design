# d-design

> **The repository has no product code.** It was deleted on 2026-08-10, along with the `v1/`, `v2/` and `v3/` documentation, because the product is being re-decided from the vision up rather than corrected. Everything is in git history — the last commit before the clear holds the whole working system.
>
> **Do not scaffold, plan, or assume a direction.** There is no roadmap, no wedge, and no chosen artefact right now. If a task seems to require one, ask instead of picking.

## What was here, so nobody rebuilds it by accident

A working system, deleted deliberately rather than abandoned: a FastAPI backend and a Next.js frontend, a Pydantic-owned `Scene` schema with TypeScript types and a Zod validator generated from it, a four-phase AI pipeline with a human gate, three art directions rendering the same tree with no branch in the renderer, and a passing acceptance run. ~316 files.

**It is not a starting point.** The decision was that the code embodies a plan under revision, so it goes back to zero. Recover a specific piece from git only if it is deliberately chosen, never because it happens to be there.

## What survives, and why

| | |
|---|---|
| `docs/coderules/` | How code stays consistent when an AI writes most of it |
| `docs/security/` | Threat model and controls, routed by threat |
| `docs/techstack/` | What runs where, which model, and **why each was chosen** |
| `docs/design/` | How **our own** app and site look — never what an engine produces |
| `docs/versions.md` | The shape the next version directory takes. Read before writing it |
| `docs/findings.md` | Evidence, not direction — measurements, model behaviour, the category, dated platform facts |
| `scripts/` | `check-docs.sh` works today. The gate and invariants pass on an empty tree and start guarding again the moment code returns |

## Commands that work today

```
./scripts/setup.sh               installs the git hooks — run once per clone
./scripts/check-docs.sh          every link resolves, every file is indexed
./scripts/hooks/pre-commit       the gate, on demand
```

There is no local infrastructure and no CI. `docker-compose.yml` and the CI workflow were deleted with the codebase — both were specific to the stack that is gone, and both get rewritten for whatever comes next.

`.env` at the repo root holds the preserved `OPENROUTER_API_KEY`. It is gitignored.

## Read before you write

Paths are **pointers, not imports** — read the file when the task touches it. Never prefix with `@`; that inlines the whole corpus into every session.

| Task touches | Read first |
|---|---|
| Any code at all | `docs/coderules/README.md` |
| Where a file or feature goes | `docs/coderules/structure.md` |
| Adding a package — **including any agent framework** | `docs/coderules/dependencies.md` |
| User input, uploads, URLs, tokens, CSP | `docs/security/README.md` (routes by threat) |
| Prompts, models, evals, AI tools | `docs/techstack/ai-stack.md`, `docs/techstack/pipeline-tools.md` |
| "Why was this chosen?" | `docs/techstack/decisions.md` |
| Writing the next version's docs | `docs/versions.md` |
| "Do we already know this?" | `docs/findings.md` |
| **What to build next** | **Nothing is decided. Ask.** |

## The non-negotiables

These governed the deleted codebase and are the **starting point** for the next one, not an inheritance. Several name a specific stack — SQLAlchemy, Drizzle, `renderer/` — and those specifics are re-confirmed when the stack is chosen. The reasoning behind each is in `docs/coderules/`, which is why that directory survived.

1. Strict types both sides. TS: no `any`, no `!`. Python: `mypy --strict`, no bare `Any`, no unexplained `# type: ignore`.
2. One schema parse per external input, at entry. Model output, tool-call arguments, and anything crossing a process boundary are all external input.
3. Expected failures return `Result`; only bugs throw/raise.
4. Import across features only through their public surface (`index.ts` / `__init__.py`).
5. No new dependency without a ledger line in `docs/coderules/dependencies.md`. Anything parsing untrusted bytes runs in an isolated worker. **An agent framework needs a ledger line too — "everyone uses it" is not one.**
6. The renderer core is pure — no `mode` prop, no `process.env`, no `typeof window`. It runs in several processes and must behave identically in all of them.
7. AI output carries no presentational values (hex/px/font/duration). The schema has no field for them.
8. The ORM only in a feature data module.
9. Every tenant-scoped query goes through **one** tenant wrapper per language. A third is a bug.
10. Anything that grants, fails closed. A `catch`/`except` returning a permissive default is a vulnerability, not error handling.
11. The gate is green — typecheck, lint, format, and any generated code regenerates with no diff — or the commit does not land.

## How to work

**Before writing a helper, grep for it.** The measured failure mode of AI-written code is duplication, not incorrectness — a second copy of something that already exists.

**Ponytail mode:** the laziest solution that works. Platform over dependency, one line over fifty, deletion over addition. Mark a deliberate shortcut with a `ponytail:` comment naming the ceiling and the upgrade path.

**Never:** give the AI a tool with side effects · authorize in middleware alone · log prompts, scene content, or recipient fields · hand-edit generated code · **install an agent framework** (LangGraph, CrewAI, Pydantic AI, …) — see `docs/techstack/ai-stack.md`.

**Commits:** subject ≤72 chars with no trailing period; a body saying what was wrong and what the project can do now; one block per file with a `path:lines · symbol()` anchor and what changed there. **No `Co-Authored-By`, no `Signed-off-by`, no tool attribution.** Full rule and the reason line numbers are paired with symbol names: `docs/coderules/commits.md`, enforced by `scripts/hooks/commit-msg`.

**Docs:** editing any `.md` means `./scripts/check-docs.sh` must still pass.
