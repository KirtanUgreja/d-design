# Code Rules

How the codebase stays consistent, clean, and cheap to change — solo, with an AI writing much of it.

## The one idea

**One source of truth, everything else derived.**

Zod schemas define the shapes; TypeScript types come from `z.infer`, never written twice. The scene schema has no field for a hex code, so the "AI emits no styling" rule is enforced by the type system before any check runs. The renderer is one pure function, so editor and published output cannot drift.

Every rule in this directory is an application of that idea: make the wrong thing unrepresentable, and you never have to police it.

It also happens to be the right defense against how this code gets written. Most of it will be Claude's, and the measured failure mode of AI-written code is not incorrectness — it is **duplication**: a second copy of something that already exists, correct in isolation, corrosive in aggregate. A rule that leaves only one place for a thing to live is a rule that failure mode cannot get past. See [ai-authorship.md](ai-authorship.md).

## The rules

| Doc | |
|---|---|
| [structure.md](structure.md) | Feature folders, public APIs, file and naming conventions |
| [typescript.md](typescript.md) | Strict TS, Zod boundaries, errors as typed Results |
| [dependencies.md](dependencies.md) | Stdlib and platform first; how a new dependency earns its place |
| [patterns.md](patterns.md) | The renderer core, data access, tenant isolation, failing closed, the model seam |
| [performance.md](performance.md) | Clarity first, measure before optimizing, the real hot paths |
| [ai-authorship.md](ai-authorship.md) | What goes wrong when Claude writes most of it, and what to do about it |
| [tooling.md](tooling.md) | The pre-commit gate, the linter choice, and the instruction file that carries these rules into every AI session |

## Non-negotiables

Eleven lines. If a change violates one, the change is wrong, not the rule.

1. **Strict TypeScript.** No `any`, no non-null `!`. The compiler is the first test.
2. **One Zod parse per input, at entry** — including **tool-call arguments**. Past that point the value is typed and trusted.
3. **Expected failures are typed Results.** Only bugs throw.
4. **Features talk through their public API** (`index.ts`), never through each other's internals.
5. **No new dependency without a one-line justification** in `dependencies.md`.
6. **The renderer core is pure and mode-free.** Behavior is injected from outside.
7. **AI output carries no presentational values.** The schema has no field for them; a runtime check backs it up.
8. **Drizzle lives in feature data modules**, never in routes or components — and those modules are marked `server-only`.
9. **Every tenant-scoped query runs inside the tenant transaction wrapper.** A pooled connection outside a transaction is a cross-tenant read.
10. **Anything that grants, fails closed.** Availability may degrade open; authorization never does.
11. **The pre-commit gate is green** — typecheck, lint, format — or the commit does not land.

Rules 9 and 10 are newer than the rest and came from the security and tech-stack work rather than from taste. Both describe failures that are silent, that look like ordinary code in review, and that no type system catches — which is exactly the profile of a rule worth writing down.

## How these relate to ponytail

This project is built in ponytail mode: the laziest solution that actually works. These rules are not extra process — they are the shape laziness takes at scale. A feature with a clear public API is *less* to hold in your head. A typed Result is *less* debugging. One derived type is *less* to keep in sync. Every rule here removes future work; none adds ceremony.

Where a rule would add ceremony, it is not here. There is no coverage target, no mandated JSDoc, no repository abstraction over an ORM that is already an abstraction. Those are complexity wearing a rulebook's clothes.
