# Structure

## Two runtimes, one repo

> **Rewritten 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md) → Locked decisions → Stack). v3 had five runtimes: `api`, `web`, a `render` service, an upload worker, and a generated `@d-design/schema` package. v4 has two. The full tree lives in [../v4/engine.md](../v4/engine.md) → "Layout"; this section says only why the split falls where it does.

The topology comes before the folders, because it decides what "cross-feature import" even means.

```
d-design/
  api/      PYTHON       FastAPI + the engine. Owns every model call, all data, the export,
                         and the headless browser that measures slides
    engine/              the pure pipeline: content · design · compose · components · qa · export
    features/            decks · generation: thin routes
    store/files.py       the only data module until phase 29 (single writer)
    worker.py            from phase 27: the separate process that runs model calls and Chromium
    settings.py          the only module that reads the environment
  bench/                 briefs, the runner and the wall (../v4/bench.md)
  web/      TYPESCRIPT   Next.js. The UI only: no database, no model key, no slide renderer
    lib/api/             types GENERATED from api's OpenAPI. Never hand-edited
```

| | Owns | Never holds |
|---|---|---|
| **`api`** | The engine, every model call, all data, the export, Chromium for QA and PDF | UI code |
| **`web`** | Screens, the editor's interaction, and (phase 29) the login UI | A database connection, a model key, or code that builds slide HTML |

**One codebase, two Python entry points, from phase 27.** `api/app.py` serves HTTP and never calls a model or a browser. `api/worker.py` runs generation jobs: it is the only process that holds the model client and Chromium, and the only writer to a deck while its job runs. Before phase 27 there is no worker; the CLI calls the engine directly.

**The boundary is the HTTP API, and OpenAPI describes it.** It is where the browser's trust ends, and the only generated thing that crosses it is the payload types ([python.md](python.md) → "Pydantic is the source of truth").

**Why the other three runtimes are gone:**
- `render` existed because Python could not server-render the React renderer. v4 slides are HTML the engine assembles, so there is nothing to server-render.
- The schema package existed to feed that renderer.
- The upload worker parsed hostile bytes for a brand kit that never reached the output.
- Uploads return only when phase 29's first brand-kit user arrives, and they return isolated ([dependencies.md](dependencies.md) → "Where a dependency runs is part of the decision").

## The server/client boundary

A second boundary, orthogonal to features, just as load-bearing, and **still true in v4**. `web` holds no data layer now, but it still has server code (route handlers, Server Actions, the Next rewrite to the API) and a client bundle.

Three mechanisms, in order of how much they are worth:

| | |
|---|---|
| **`import 'server-only'`** at the top of anything in `web` that holds a secret or talks to the API with server-side credentials (phase 29) | A client component importing it becomes a build error. Cheap, absolute, and it makes the boundary a compiler concern instead of a discipline concern |
| **Shape responses in `api`, not in the component** | The API returns what the screen needs, never whole records "to be filtered later". A deck list returns thumbnails, never image payloads (v3's list fetched every image and threw it away) |
| **React's taint APIs** (`experimental_taintObjectReference`, `experimental_taintUniqueValue`) | Runtime enforcement for the values most damaging to leak (tokens, from phase 29). A backstop under the two above, not a replacement |

**Server Actions and Server Functions are public HTTP endpoints.** They look like local function calls, which is the whole problem: a reader sees a function, an attacker sees a URL. Each one authenticates and authorizes on its own ([../security/platform-and-packages.md](../security/platform-and-packages.md)). The manual checklist in [../security/testing.md](../security/testing.md) says to call every route with no session and with another user's session. Server Actions count as routes for that purpose.

## Feature folders

The codebase is organized by feature, not by layer. Each feature is a folder that owns everything it needs and exposes one public surface.

```
api/features/                        web/features/
  decks/                               composer/
    __init__.py    ← the public API       index.ts      ← the public API
    routes.py                           outline/
  generation/                           looks/  watch/
    __init__.py                         editor/
    routes.py                              index.ts
                                           slide-frame.tsx  ← the sandboxed iframe
api/store/files.py ← the data module     present/  export/

api/engine/        ← not a feature: the pure core, with one public API (engine/__init__.py)
```

**The two trees are deliberately the same shape**, because the rule should not change when the language does. A feature owns everything it needs and exposes one public surface; `api/store/files.py` is the only place storage appears; tests sit next to what they test.

**Imports cross only through the public surface**: `index.ts` on one side, `__init__.py` on the other.
- `editor` may import from `present`'s index; it may not reach into `present`'s internals.
- The worker and the CLI call the engine through `engine/__init__.py`, never `engine/compose/slide.py` directly. Routes do not call the engine's model or browser paths at all; they enqueue a job.
- Enforced by lint, not by discipline: `import/no-internal-modules` scoped to feature dirs on one side; Ruff's `TID252` plus an import-linter contract on the other.

Why: a feature you can only touch through its public API is a feature whose insides you can change without breaking anything. It is also less to understand, because the index is the whole contract.

### Shared code

```
api/                                 web/
  engine/     the pure pipeline        lib/       cross-cutting helpers
  lib/        result, ids              lib/api/   generated types · the one fetch client · SSE parsing
  store/      files.py, the data module
  features/   thin routes              app/       Next.js routes, thin
```

`lib/` is for things every feature uses and no feature owns: the `Result` type, id generation, the API client. If something in `lib/` is used by one feature, it belongs in that feature.

Routes are thin on both sides. A route parses its input, calls a feature's public function, and returns the result. No business logic, no storage access, no branching beyond request shape.

**The Pydantic models in `api/engine/models.py`, plus each route's request and response models, are the source of truth for every shape `web` sees.** `web` consumes types generated from OpenAPI. There is no hand-written `web/schema/`, and creating one is the drift ([python.md](python.md)).

### The marketing site is a route group, not a third runtime

It belongs in `web/app/(marketing)/` ([../design/website.md](../design/website.md)): statically generated, no data, no feature imports. The one thing that makes it worth having is a real exported deck shown live on the page. That is an iframe of an export file, exactly as present mode shows it; it is not re-rendered.

Two boundaries it must not cross, both of which look like conveniences at the time:
- **Marketing pages do not import feature internals.** They are the thinnest routes in the codebase. If one needs data, it is asking for a product surface and belongs in the app.
- **Our chrome's tokens are not a deck theme's.** Tailwind styles ours. A deck's theme is CSS custom properties inside its own document (an iframe, or the export file), and no file uses both. The document boundary keeps them apart in both directions: a deck's CSS cannot leak into our chrome, and a marketing page cannot reach for a deck's variables because they looked right.

The recorded SSE event logs the marketing demo replays are **fixtures, not code**. They live next to the bench briefs in repo-root `bench/` ([../v4/bench.md](../v4/bench.md)) and nothing imports them.

## Files

- **One primary export per file, named for the file.** `outline-card.tsx` exports `OutlineCard`; `storyline.py` exports `plan_storyline`. Grep finds it, imports are predictable, and there are no grab-bag files.
- **kebab-case TypeScript filenames** (`slide-frame.tsx`), **snake_case Python filenames** (`decks_data.py`). Each language's own convention; fighting either buys nothing.
- **PascalCase** for components, types, and Pydantic models. **camelCase** in TypeScript and **snake_case** in Python, for functions and variables. One rule per language, no per-file debate.
- **Colocate.** A module, its test, and the types it owns live side by side. No distant `__tests__/` or `types/` tree.
- **No barrels except the feature public API.** The only `index.ts` or re-exporting `__init__.py` files are the ones that *are* a feature's surface (and `engine/__init__.py`). No re-export chains that hide where a thing actually lives.
- **Prompts are files**, versioned by name (`prompts/<stage>.v<N>.md`), not strings inside Python ([../v4/engine.md](../v4/engine.md) → "Layout").

**Do not transliterate one language's conventions into the other.** `snake_case` filenames in `web` and `kebab-case` modules in `api` are the same mistake: a codebase that reads as though it were translated rather than written. The *rules* are parallel; the *spellings* are native.

## File size is a signal

A file growing past a few hundred lines usually means it is doing more than one thing. That is a prompt to split by responsibility, not a hard limit to game. The goal is a file you can hold in your head at once, which is also the file an AI edits most reliably.

## Test

Cross-feature reach-through and import cycles fail the gate.
- **In `web`,** `eslint-plugin-import-boundaries` encodes exactly this model: a boundary's `index.ts` is its public surface, and everything else in the folder is private. Check whether it fits before writing a custom rule ([tooling.md](tooling.md)).
- **In `api`,** an import-linter contract says `engine` imports no `features`, `fastapi` or `starlette`, and `features` reach `engine` only through its package root.

That is the whole enforcement; the structure defends itself.

## One cost worth naming

A feature folder is a context boundary for the reader, which is the point. It is also a context boundary for whatever is writing the code, and that has a price: code being written inside `engine/compose/` has no particular reason to notice that `engine/qa/` already measures text boxes.

This is the mechanism behind the duplication numbers in [ai-authorship.md](ai-authorship.md). It is also why each public surface (`engine/__init__.py`, and every feature's `index.ts`) should stay short enough to read on one screen. It is the catalog of what already exists, and a catalog nobody reads is not one.
