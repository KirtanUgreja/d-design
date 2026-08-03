# Structure

## Three deployables, two repos, one shared package

Before the folders, the topology — because it determines what "cross-feature import" even means ([../techstack/infrastructure.md](../techstack/infrastructure.md)).

```
d-design/                    (repo 1)
  src/app/                   Next.js routes
  src/features/              the feature folders below
  src/schema/                the Zod source of truth  ─┐
  src/lib/                                             │ published as
  worker/                    job worker entry point    │ @d-design/schema
                                                       │
d-design-fetch/              (repo 2) ◀────────────────┘
  hostile input only: URL fetch, screenshots, document parsing
```

**The app and the job worker are one codebase with two entry points.** The worker is not a separate project — it imports the same features, the same data modules, and the same renderer. That is what lets publishing and the visual verification loop run there ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)) without duplicating anything.

**Only the fetch worker is separate**, because its isolation is a security property rather than an organizational one. It gets `@d-design/schema` and nothing else. **It never gets the renderer** — page-making capability does not belong in the container that handles attackers' input.

The consequence for this document: everything below describes repo 1. Repo 2 is small enough that it needs no structure beyond a handful of files.

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
src/features/
  generation/
    index.ts            ← the ONLY thing other features import
    pipeline.ts
    prompts.ts
    repair.ts
    generation.data.ts  ← Drizzle queries for this feature
    generation.test.ts
  editor/
    index.ts
    ...
  renderer/
    index.ts
    scene-renderer.tsx  ← the pure core
    blocks/
    ...
  publish/
  brand/
```

**Imports cross only through `index.ts`.** `editor` may import from `renderer`'s index; it may not reach into `renderer/blocks/headline.tsx`. This is enforced by a lint rule (`import/no-internal-modules` scoped to feature dirs), not by discipline.

Why: a feature you can only touch through its public API is a feature you can change the insides of without breaking anything. It is also less to understand — the index is the whole contract.

### Shared code

```
src/
  schema/     Zod schemas + inferred types. The source of truth
  lib/        genuinely cross-cutting helpers (result, storage, ids)
  db/         Drizzle client, migrations
  app/        Next.js routes — thin, delegate to features
```

`lib/` is for things every feature uses and no feature owns — the `Result` type, `storage.ts`, id generation. If something in `lib/` is used by one feature, it belongs in that feature.

Routes in `app/` are thin. A route parses its input, calls a feature's public function, and returns the result. No business logic, no Drizzle, no branching beyond request shape.

## Files

- **One primary export per file, named for the file.** `scene-renderer.tsx` exports `SceneRenderer`. `pipeline.ts` exports `runPipeline`. Grep finds it, imports are predictable, no grab-bag files.
- **kebab-case filenames.** `scene-renderer.tsx`, `art-direction.ts`.
- **PascalCase** for components and types, **camelCase** for functions and variables. One rule, no per-file debate.
- **Colocate.** `scene-renderer.tsx`, `scene-renderer.test.ts`, and the types it owns live side by side. No distant `__tests__/` or `types/` tree.
- **No index barrels except the feature public API.** The only `index.ts` files are the ones that *are* a feature's surface. No re-export chains that hide where a thing actually lives.

## File size is a signal

A file growing past a few hundred lines usually means it is doing more than one thing. That is a prompt to split by responsibility, not a hard limit to game. The goal is a file you can hold in your head at once — which is also the file an AI edits most reliably.

## Test

Cross-feature reach-through and import cycles fail the gate. `eslint-plugin-import-boundaries` encodes exactly this model — a boundary's `index.ts` is its public surface, everything else in the folder is private — so check whether it fits before writing a custom rule ([tooling.md](tooling.md)). That is the whole enforcement; the structure defends itself.

## One cost worth naming

A feature folder is a context boundary for the reader, which is the point. It is also a context boundary for whatever is writing the code, and that has a price: code being written inside `editor/` has no particular reason to notice that `renderer/` already solved the same problem. This is the mechanism behind the duplication numbers in [ai-authorship.md](ai-authorship.md), and the reason a feature's `index.ts` should stay short enough to read in one screen — it is the catalog of what already exists, and a catalog nobody reads is not one.
