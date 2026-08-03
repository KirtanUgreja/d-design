# Structure

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
