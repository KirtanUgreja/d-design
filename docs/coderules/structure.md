# Structure

## Five runtimes, five repos, one generated package

Before the folders, the topology — because it determines what "cross-feature import" even means ([../techstack/infrastructure.md](../techstack/infrastructure.md), [../techstack/backend.md](../techstack/backend.md)).

```
d-design-api/           PYTHON      api + jobs — two entry points, one codebase
  schema/                           the Pydantic source of truth  ──┐
  features/                         the feature folders below       │ CI generates
  ai/complete.py                    the one model seam              │      ▼
  db/tenant.py                      as_user — one of two            │  @d-design/schema
                                                                    │  (types + Zod)
d-design-web/           TYPESCRIPT  editor, renderer, Better Auth ◀──┤
d-design-render/        TYPESCRIPT  deck tree → HTML, Playwright ◀──┤
d-design-fetch/         TYPESCRIPT  hostile input only            ◀──┘
d-design-schema/        GENERATED   the generated types — never hand-edited
```

**`api` and `jobs` are one codebase with two entry points.** The worker is not a separate project — it imports the same features, the same data modules, and the same seam. Same relationship the app and job worker used to have, moved to the other language.

**Everything else is separate, and the separations are not all the same kind:**

| | Separate because | Kind |
|---|---|---|
| **fetch worker** | Its isolation is a security property. No DB, no VPC route, and **never the renderer** | Trust |
| **render** | Python cannot SSR React, and the renderer must have exactly one implementation ([patterns.md](patterns.md) rule 2) | Language |
| **web** | It is the browser half, and it holds auth | Deployment |

**Only the first is a security boundary.** The other two are consequences of the Python move, and labelling them honestly is what stops someone reasoning "these are isolated services, therefore this is safe" about a split that was never a control.

The consequence for this document: everything below describes `api` and `web`, whose conventions are deliberately parallel. `render` and `fetch` are each small enough to need no structure beyond a handful of files.

## The server/client boundary

A second boundary, orthogonal to features and just as load-bearing. Next.js's own security guidance names the Data Access Layer as the primary defense against accidental data exposure — which is the `*.data.ts` rule this project already had, arrived at independently.

Three mechanisms, in order of how much they are worth:

| | |
|---|---|
| **`import 'server-only'`** at the top of every `*.data.ts`, the model seam, and anything holding a secret | A build-time error if a client component ever imports it. Cheap, absolute, and it makes the boundary a compiler concern instead of a discipline concern |
| **The data module returns exactly what the caller needs** | A `recipients` row has fields that must never reach a browser. Shaping happens in the data module, not in the component that forgot |
| **React's taint APIs** (`experimental_taintObjectReference`, `experimental_taintUniqueValue`) | Runtime enforcement for the objects and values that would be most damaging to leak. A backstop under the two above, not a replacement |

**Server Actions and Server Functions are public HTTP endpoints.** They look like local function calls, which is the entire problem — a reader sees a function, an attacker sees a URL. Every one authenticates and authorizes on its own, and does it at the data layer ([../security/platform-and-packages.md](../security/platform-and-packages.md)). The manual checklist in [../security/testing.md](../security/testing.md) already says to call every route with no session and with another tenant's session; Server Actions are routes for that purpose.

## Feature folders

The codebase is organized by feature, not by layer. Each feature is a folder that owns everything it needs and exposes one public surface.

```
api/features/                        web/src/features/
  generation/                          editor/
    __init__.py    ← the public API      index.ts     ← the public API
    build.py                             ...
    prompts/build.py                   renderer/
    tools.py                             index.ts
    checks.py                            scene-renderer.tsx  ← the pure core
    generation_data.py  ← SQLAlchemy     blocks/
    test_generation.py                 auth/
  intake/  director/  publish/           auth.data.ts        ← Drizzle, auth tables
  brand/                                 ...
```

**The two trees are deliberately the same shape**, because the rule should not change when the language does. A feature owns everything it needs and exposes one public surface; the data module is the only place the ORM appears; tests sit next to what they test.

**Imports cross only through the public surface** — `index.ts` on one side, `__init__.py` on the other. `editor` may import from `renderer`'s index; it may not reach into `renderer/blocks/headline.tsx`. Enforced by a lint rule (`import/no-internal-modules` scoped to feature dirs; Ruff's `TID252` plus an import-linter contract on the Python side), not by discipline.

Why: a feature you can only touch through its public API is a feature you can change the insides of without breaking anything. It is also less to understand — the index is the whole contract.

### Shared code

```
api/                                 web/src/
  schema/    Pydantic. THE source      lib/    cross-cutting helpers
  lib/       result, storage, ids      db/     Drizzle client — auth tables only
  db/        SQLAlchemy, tenant.py     app/    Next.js routes — thin
  ai/        complete.py — the seam
  routes/    FastAPI routers — thin
```

`lib/` is for things every feature uses and no feature owns — the `Result` type, storage, id generation. If something in `lib/` is used by one feature, it belongs in that feature.

Routes are thin on both sides. A route parses its input, calls a feature's public function, and returns the result. No business logic, no ORM, no branching beyond request shape.

**`api/schema/` is the source of truth for the whole system and has no TypeScript counterpart** — `web` consumes `@d-design/schema`, which is generated. There is no `web/src/schema/`, and creating one is the drift ([python.md](python.md)).

### The marketing site is a route group, not a third repo

It arrives in v3 ([../design/website.md](../design/website.md)) and it belongs in `app/(marketing)/` — statically generated, no data layer, no feature imports beyond `renderer`'s index for the one thing that makes it worth having: a real published artifact embedded live in the page.

Two boundaries it must not cross, both of which look like conveniences at the time:

- **Marketing pages do not import feature internals.** They are the thinnest routes in the codebase. If one needs a database read, it is asking for a product surface and belongs in the app
- **Our chrome's design tokens are not a design family's.** Tailwind for one, CSS custom properties for the other, and no file imports both ([../techstack/frontend.md](../techstack/frontend.md)). The lint rule already scoped to `renderer/` is what keeps the boundary from eroding in the easy direction; nothing yet stops the hard direction, which is a marketing page reaching for a family variable because it looked right

The recorded SSE event logs the marketing demo replays are **fixtures, not code** — `evals/recordings/`, next to the golden briefs, imported by nothing.

## Files

- **One primary export per file, named for the file.** `deck-renderer.tsx` exports `DeckRenderer`. `build.py` exports `run_build`. Grep finds it, imports are predictable, no grab-bag files.
- **kebab-case TypeScript filenames** (`deck-renderer.tsx`), **snake_case Python filenames** (`generation_data.py`). Each language's own convention — fighting either buys nothing.
- **PascalCase** for components, types, and Pydantic models. **camelCase** in TypeScript, **snake_case** in Python, for functions and variables. One rule per language, no per-file debate.
- **Colocate.** A module, its test, and the types it owns live side by side. No distant `__tests__/` or `types/` tree.
- **No barrels except the feature public API.** The only `index.ts` / re-exporting `__init__.py` files are the ones that *are* a feature's surface. No re-export chains that hide where a thing actually lives.

**Do not transliterate one language's conventions into the other.** `snake_case` filenames in `web` and `kebab-case` modules in `api` are both the same mistake — a codebase that reads as though it were translated rather than written. The *rules* are parallel; the *spellings* are native.

## File size is a signal

A file growing past a few hundred lines usually means it is doing more than one thing. That is a prompt to split by responsibility, not a hard limit to game. The goal is a file you can hold in your head at once — which is also the file an AI edits most reliably.

## Test

Cross-feature reach-through and import cycles fail the gate. `eslint-plugin-import-boundaries` encodes exactly this model — a boundary's `index.ts` is its public surface, everything else in the folder is private — so check whether it fits before writing a custom rule ([tooling.md](tooling.md)). That is the whole enforcement; the structure defends itself.

## One cost worth naming

A feature folder is a context boundary for the reader, which is the point. It is also a context boundary for whatever is writing the code, and that has a price: code being written inside `editor/` has no particular reason to notice that `renderer/` already solved the same problem. This is the mechanism behind the duplication numbers in [ai-authorship.md](ai-authorship.md), and the reason a feature's `index.ts` should stay short enough to read in one screen — it is the catalog of what already exists, and a catalog nobody reads is not one.
