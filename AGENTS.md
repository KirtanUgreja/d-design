# d-design

AI presentation-experience engine. The AI emits **content + intent**; a separate art-direction token layer resolves intent into type, spacing, color, easing, duration. **The AI never writes styling.** That one constraint is what makes editing safe, reskin cheap, and the product boundary real.

**Status: design complete, nothing built.** `docs/` is the spec. Start at `docs/README.md`.

## Read before you write

Paths are **pointers, not imports** — read the file when the task touches it. Do not prefix with `@`; that inlines the whole corpus into every session.

| Task touches | Read first |
|---|---|
| Any code at all | `docs/coderules/README.md` |
| Where a file or feature goes | `docs/coderules/structure.md` |
| Types, Zod, error handling | `docs/coderules/typescript.md` |
| Adding a package | `docs/coderules/dependencies.md` |
| Renderer, data access, model calls | `docs/coderules/patterns.md` |
| DB, auth, tenants, RLS | `docs/coderules/patterns.md` + `docs/security/tenancy-and-data.md` |
| User input, uploads, URLs, tokens, CSP | `docs/security/README.md` (routes by threat) |
| Prompts, models, evals, AI tools | `docs/techstack/ai-stack.md`, `docs/techstack/pipeline-tools.md` |
| Where something runs or deploys | `docs/techstack/infrastructure.md` |
| "Why was this chosen?" | `docs/techstack/decisions.md` |
| The scene tree | `docs/v1/scene-schema.md` |
| What to build next | `docs/v1/spec.md` → Build order |

## Non-negotiable

1. Strict TS. No `any`, no `!`.
2. One Zod parse per external input, at entry. Model output, tool-call arguments, and Server Action inputs are all external input.
3. Expected failures return `Result`; only bugs throw.
4. Import across features only through their `index.ts`.
5. No new dependency without a ledger line in `docs/coderules/dependencies.md`. Anything parsing untrusted bytes goes in the fetch worker.
6. `renderer/` core is pure — no `mode` prop, no `process.env`, no `typeof window`. It runs in three processes and must behave identically in all of them.
7. AI output carries no presentational values (hex/px/font/duration). The schema has no field for them.
8. Drizzle only in `*.data.ts` inside a feature, and those files start with `import 'server-only'`.
9. Every tenant-scoped query goes through the `asUser()` transaction wrapper. A `db.` call outside it is a cross-tenant read waiting to happen.
10. Anything that grants, fails closed. A `catch` returning a permissive default is a vulnerability, not error handling.
11. The gate is green — typecheck, lint, format — or the commit does not land.

## How to work

**Before writing a helper, grep for it.** The measured failure mode of AI-written code is duplication, not incorrectness — a second copy of something that already exists. Rules 6, 8, 9 and the model seam each exist because there must be exactly one of that thing.

**Ponytail mode:** the laziest solution that works. Platform over dependency, one line over fifty, deletion over addition. Mark a deliberate shortcut with a `ponytail:` comment naming the ceiling and the upgrade path.

**Never:** loosen rule 7 with a `styleOverride` field · add `allow-same-origin` to the Slot sandbox · give the AI a tool with side effects · authorize in middleware alone · log prompts, scene content, or recipient fields.

**Docs:** editing any `.md` means `./scripts/check-docs.sh` must still pass — every link resolves, every file is listed in its directory README.
