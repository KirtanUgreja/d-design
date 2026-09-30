# Code Rules

> How the codebase stays consistent, clean, and cheap to change — solo, with an AI writing much of it.

**Start here:** the [Non-negotiables](#non-negotiables) below. Eleven lines, and rules 9 and 10 prevent bugs that look like correct code in review.

**Writing code right now?** The condensed version lives in `AGENTS.md` at the repo root — see [tooling.md](tooling.md) → "The instruction file".

> **Updated 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)). Rules 2, 6, 7, 8, 9 and 11 changed; the reasons are in [Non-negotiables](#non-negotiables) below.

## The one idea

**One source of truth, everything else derived.**

Pydantic models define every shape that crosses a boundary. The model's JSON Schema comes from `model_json_schema()`. FastAPI publishes the same models as OpenAPI, and the TypeScript types `web` uses are **generated** from that document. Nothing is written twice, in either language.

The deck's look has one source too: **the theme**. The model composes each slide's HTML and layout freely, but colour and type may only reference the theme's tokens, and a lint at entry rejects anything else. So the design system stays the single source of visual truth without taking composition away from the model ([../v4/spec.md](../v4/spec.md) → Locked decisions → Token rule).

The engine is one set of pure functions, and the CLI, the routes and the bench all call it. The app renders no slide of its own, so what you edit, present and download come out of the same assembly code.

Every rule in this directory applies that idea:
- **A type** makes the wrong thing unrepresentable wherever a type can do it.
- **A check at entry** makes it detectable wherever a type cannot.

**Two languages, one owner per concern** (2026-09-26, [../v4/spec.md](../v4/spec.md) → Locked decisions → Stack).
- **Python** owns the engine, every model call, all data and the export.
- **TypeScript** owns only the UI.
- **The boundary** is the HTTP API that FastAPI describes as OpenAPI. The only generated artefact that crosses it is the payload types.

v3 split concerns across that boundary instead: a TypeScript renderer fed by a Pydantic→Zod `Deck` codegen, two ORMs, two auth halves, and two tenant wrappers. Every split needed a gate standing in for a structure. v4 removes the splits rather than gating them.

It also happens to be the right defense against how this code gets written. Most of it will be Claude's, and the measured failure mode of AI-written code is not incorrectness. It is **duplication**: a second copy of something that already exists, correct in isolation, corrosive in aggregate. A rule that leaves only one place for a thing to live is a rule that failure mode cannot get past. See [ai-authorship.md](ai-authorship.md).

## The rules

| Doc | |
|---|---|
| [structure.md](structure.md) | Two runtimes, feature folders, public APIs, file and naming conventions |
| [python.md](python.md) | Strict Python, Pydantic at every boundary, OpenAPI as the published contract, `Result` in a language without unions |
| [typescript.md](typescript.md) | Strict TS, OpenAPI-generated types, errors as typed Results |
| [dependencies.md](dependencies.md) | Stdlib and platform first; how a new dependency earns its place |
| [patterns.md](patterns.md) | The token rule, engine purity, data access, tenant isolation, failing closed, the model seam |
| [performance.md](performance.md) | Clarity first, measure before optimizing, the real hot paths |
| [ai-authorship.md](ai-authorship.md) | What goes wrong when Claude writes most of it, and what to do about it |
| [tooling.md](tooling.md) | The pre-commit gate, the linter choice, and the instruction file that carries these rules into every AI session |
| [commits.md](commits.md) | What a commit message must say, why line numbers are paired with symbol names, what the `commit-msg` hook enforces, and how phase branches are named |

## Non-negotiables

Eleven lines. If a change violates one, the change is wrong, not the rule.

1. **Strict types, both languages.** TypeScript: no `any`, no non-null `!`. Python: full annotations, `mypy --strict`, no bare `Any`, no `# type: ignore` without a reason on the same line. The type checker is the first test.
2. **One parse per input, at entry.**
   - In `api`, Pydantic parses request bodies, **model output** and web-search results.
   - Slide HTML is parsed, sanitized (`nh3`) and linted (`tinycss2`) at entry.
   - In `web`, every API payload is parsed once, at the fetch boundary, against the OpenAPI-generated contract.
   - Past that point the value is typed and trusted.
3. **Expected failures are typed Results.** Only bugs throw.
4. **Features talk through their public API** (`index.ts` / `__init__.py`), never through each other's internals.
5. **No new dependency without a one-line justification** in `dependencies.md`. **An agent framework needs one too**, and "everyone uses it" is not one.
6. **The engine is pure.** `api/engine/` imports no web framework and reads no environment; the model client, event sink, storage and browser pool are injected. The CLI, the worker and the bench call the same functions. From phase 27 model calls and Chromium run only in the worker process (`api/worker.py`); the API process never calls a model or a browser. There is no TypeScript renderer.
7. **Model output references the theme for colour and type, never raw values.** Colour, `font-family`, `font-size` and `font-weight` may only be theme tokens (`var(--…)`, or a weight the theme embeds). Layout is free. Slide HTML is sanitized and its CSS linted at entry: no gradients, blur, glow, scripts, handlers, links or external URLs. *This replaces "AI output carries no presentational values" (2026-09-26). That rule had the model fill a form, and it capped every deck at about five visual variables ([../findings.md](../findings.md)).*
8. **Storage is touched in one place**, never in routes or the engine. Until phase 29 that is `api/store/files.py`, the only data module, under a single-writer rule ([patterns.md](patterns.md) rule 3). From phase 29 it is SQLAlchemy in Python `*_data.py` modules. `web` has no database and no ORM.
9. **Every tenant-scoped query runs inside the tenant wrapper.** There is **exactly one**, in Python, and it arrives with Postgres in phase 29 ([patterns.md](patterns.md) rule 4). A second is a bug.
10. **Anything that grants, fails closed.** Availability may degrade open; authorization never does.
11. **The pre-commit gate is green**: typecheck, lint, format, tests, **the OpenAPI-generated types regenerate with no diff**, and the docs check. Otherwise the commit does not land.

Rules 9 and 10 came from the security and tech-stack work rather than from taste. Both describe failures that are silent, that look like ordinary code in review, and that no type system catches. That is exactly the profile of a rule worth writing down.

**Rules 2, 6, 7, 8, 9 and 11 changed shape on 2026-09-26** ([../v4/spec.md](../v4/spec.md)), in the same direction as the rest of v4: a split that needed a gate became a single owner.
- One tenant wrapper instead of two.
- No `Deck` codegen and no second renderer.
- Rule 7 no longer forbids the model to style; it constrains what the model's styling may reference.

## Find it fast

| If you need… | Go to |
|---|---|
| Where a file goes, and the repo layout | [structure.md](structure.md) → "Two runtimes, one repo", "Feature folders"; the full tree is in [../v4/engine.md](../v4/engine.md) → "Layout" |
| The server/client boundary — `server-only`, taint, Server Actions | [structure.md](structure.md) → "The server/client boundary" |
| Naming and file conventions | [structure.md](structure.md) → "Files" |
| Which Python, and what the type checker is set to | [python.md](python.md) → "Strict, and what that means here" |
| **Where the shapes live, and how they reach `web`** | [python.md](python.md) → "Pydantic is the source of truth" |
| Why slide HTML is parsed rather than schema-validated | [python.md](python.md) → "Slide HTML is not a schema" |
| `Result` in Python | [python.md](python.md) → "Errors" |
| Which TypeScript, and the TS 7 compiler-API caveat | [typescript.md](typescript.md) → "Which TypeScript — and the one thing that breaks" |
| How `web` gets its API types | [typescript.md](typescript.md) → "Types come from OpenAPI, never written twice" |
| What counts as external input | [python.md](python.md) and [typescript.md](typescript.md) → "Trust boundaries: one parse, at entry" |
| `Result` vs throwing | [typescript.md](typescript.md) → "Errors" |
| Whether to add a package | [dependencies.md](dependencies.md) → "Adding one", "The ledger" |
| The packages v4 is expected to add | [dependencies.md](dependencies.md) → "v4" |
| Supply-chain install hardening | [dependencies.md](dependencies.md) → "Installing one safely" |
| Where a risky dependency may run | [dependencies.md](dependencies.md) → "Where a dependency runs is part of the decision" |
| **What model-written CSS may reference** | [patterns.md](patterns.md) → rule 1, the token rule |
| Why the engine is pure, and why `web` never renders a slide | [patterns.md](patterns.md) → rule 2 |
| The tenant wrapper | [patterns.md](patterns.md) → rule 4 — **the most dangerous code in the backend** |
| The fail-closed rule, with examples | [patterns.md](patterns.md) → rule 5 |
| The model seam | [patterns.md](patterns.md) → rule 6 |
| What to optimize, and what not to | [performance.md](performance.md) → "The only hot paths", "What not to optimize" |
| The pre-commit gate and lint rules | [tooling.md](tooling.md) → "The pre-commit gate" |
| What CI runs | [tooling.md](tooling.md) → "What CI runs" |
| What gates a merge, what gates a phase | [tooling.md](tooling.md) → "Evals are the bench, and the wall gates phases"; [../v4/bench.md](../v4/bench.md) |
| Linter choice, and when to switch to Biome | [tooling.md](tooling.md) → "Which linter and formatter" |
| What goes wrong when an AI writes the code | [ai-authorship.md](ai-authorship.md) → "What actually goes wrong — measured" |
| Which parts of a diff to actually read | [ai-authorship.md](ai-authorship.md) → "The four working rules" |
| Phase branch names | [commits.md](commits.md) → "Branches" |

## How these relate to ponytail

This project is built in ponytail mode: the laziest solution that actually works. These rules are not extra process; they are the shape laziness takes at scale.
- A feature with a clear public API is *less* to hold in your head.
- A typed Result is *less* debugging.
- One derived type is *less* to keep in sync.

Every rule here removes future work; none adds ceremony.

Where a rule would add ceremony, it is not here. There is no coverage target, no mandated JSDoc, no repository abstraction over an ORM that is already an abstraction. Those are complexity wearing a rulebook's clothes.

## Connects to

| | |
|---|---|
| [../techstack/README.md](../techstack/README.md) | What the code actually runs on — these rules are downstream of those choices |
| [../security/README.md](../security/README.md) | Where rules 9 and 10 come from, and what they are defending |
| [../v4/engine.md](../v4/engine.md) | The layout, the data model and the model seam these rules govern |
| [../v4/design-engine.md](../v4/design-engine.md) | The slide contract and the lint that rule 7 describes |
