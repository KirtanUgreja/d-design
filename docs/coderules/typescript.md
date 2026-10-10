# TypeScript

The UI half: **`web` only**, as of 2026-09-26. It builds no slide HTML, holds no database connection and no model key. It shows documents the engine produced and calls the API ([python.md](python.md), [../v4/engine.md](../v4/engine.md) → "Layout"). The two halves meet at one HTTP API described by OpenAPI; this document is downstream of it.

## Strict, and then stricter

`tsconfig` runs `strict: true` plus `noUncheckedIndexedAccess` and `erasableSyntaxOnly`. ESLint bans two things the compiler allows:

- **`any`**: use `unknown` and narrow, or type it properly. `any` deletes the compiler.
- **the non-null `!` operator**: it is a lie to the type system. If a value can be null, handle it. If it truly cannot, restructure so the type reflects that.

The compiler is the first and cheapest test. Most bugs that matter are ones it already catches for free; the rules above stop you switching it off one expression at a time.

`erasableSyntaxOnly` is worth calling out:
- It makes TS `enum`, `namespace`, and class parameter properties **compile errors**. That retires the `no-restricted-syntax` lint rule this project would otherwise need for the enum ban below. A compiler flag beats a lint rule: it is one line, it cannot be disabled per file without it being obvious, and it runs first.
- It keeps every `.ts` file valid input for Node's native type stripping. That costs nothing to preserve and occasionally saves a build step.

## Which TypeScript — and the one thing that breaks

**TypeScript 7.0** shipped 8 July 2026, with the compiler rewritten in Go:
- Full builds are generally 8–12× faster, with roughly 18% less memory. Microsoft's own VS Code build went from 125.7s to 10.6s.
- It turns `strict` and `esnext` on by default, and makes TypeScript 6.0's deprecations hard errors. For this project, the defaults finally match what the rules already demanded.

A 10× typecheck is not a vanity number here. `tsc --noEmit` sits in the pre-commit gate ([tooling.md](tooling.md)), and a gate that returns in under a second is a gate you never route around.

**The catch, and it is a real one: TypeScript 7.0 ships without a public compiler API.** Anything that reads the type graph programmatically cannot run on it, and that means `typescript-eslint` above all. A stable API is planned for 7.1.

The documented interim pattern, and the one to use:

```jsonc
// package.json — TS 7 for the project, TS 6 pinned for the linter only
"devDependencies": {
  "typescript": "^7.0",
  "@typescript/typescript6": "npm:typescript@^6.0"   // typescript-eslint reads this
}
```

Typecheck runs on 7; type-aware lint runs on the pinned 6. That is two compilers on disk and one line of config, and it is temporary. When 7.1 lands the API, the pin is a ledger entry to delete, and deletion is a feature ([dependencies.md](dependencies.md)).

It is also a reason to be unhurried. Nothing in this project needs 7 on day one, and the gate is fast enough on 6 for a codebase this size. Take it when the ecosystem has caught up, not because the number is large.

## Types come from OpenAPI, never written twice

**Superseded twice**:
- First this section said *"Zod is the source of truth."*
- Then it said Pydantic was, via a generated `@d-design/schema` package of types and a Zod validator for the whole `Deck` tree.

As of 2026-09-26, `web` has no renderer and does no offline tree editing, because slides are HTML documents the engine produced. What it needs are the API's payload types. They are generated from FastAPI's OpenAPI with `openapi-typescript` into `web/lib/api/schema.d.ts` ([python.md](python.md) → "Pydantic is the source of truth").

```ts
// web/lib/api/schema.d.ts — GENERATED from api's OpenAPI. Do not edit.
export interface components { schemas: { Deck: …; SlidePlan: …; Fact: … } }
```

The rule that matters most is short: **never hand-edit generated code, and never hand-write a type that duplicates a generated one.** The gate regenerates and fails on a diff, so a hand-edit does not survive a commit. It will still look entirely reasonable in review, which is why it is stated here rather than left to the gate.

If you want a type the generated file does not give you, the Pydantic model or the route's response model is missing something. **Change it there.** A local type alias for a generated shape is the first copy, and the first copy is where the drift starts.

### Why there is no Zod-for-the-deck any more

v3 generated a validator so the editor could revalidate a patched block tree offline, without a round trip. v4's editor works differently (../v4/plan/28-editor.md):
- Text is edited in place inside the slide's own document.
- The change goes to the API, which re-runs QA.
- The checks that matter (sanitize, lint, measure) run where the browser that measures them runs.

An offline editor is not a v4 goal. If one becomes a goal, it will be a decision with a trigger, not a validator that drifted in.

## Trust boundaries: one parse, at entry

**Every external input is parsed exactly once, at the point it enters `web`. Past that point it is typed and trusted.**

External means:
- API responses and SSE events
- URL params
- anything a user types
- **the DOM of a slide iframe** the editor reads back after an inline edit

All of it is `unknown` until parsed, and none of it is re-validated downstream.

- **API responses:** the generated types say what the shape should be. The runtime check that proves it happens once, in `lib/api/client.ts` and `lib/api/events.ts`. The validator behind that check is chosen in phase 27, with a ledger line. Generate it from the same OpenAPI document; never hand-write it ([dependencies.md](dependencies.md)).
- **The slide iframe is AI-authored markup, even after sanitizing.** Read edits back as text from `data-field` nodes only (`textContent`), and send the text to the API. Never move `innerHTML` out of the frame into our own DOM ([patterns.md](patterns.md) rule 2).

This mirrors the security model's trust boundaries exactly ([../security/README.md](../security/README.md)). Scattered re-validation is the anti-pattern: it drifts out of sync with the source and hides where the real boundary is. One parse point per input, and the type carries the guarantee from there.

Server Actions have the same shape of trap: they read as local calls, and they are public HTTP endpoints ([structure.md](structure.md)). **The rule generalizes: if a value crossed a process boundary to get here, it is external, however local the call site looks.**

## Errors: typed Results for the expected, throw for the impossible

Two categories, two mechanisms.

**Expected failures return a `Result`.** These happen in normal operation: the API is unreachable, the stream drops mid-build, a slide comes back flagged, an edit is rejected by QA, the input fails validation. The caller must handle them, and the compiler makes sure it does.

```ts
// lib/result.ts
export type Result<T, E = AppError> =
  | { ok: true; value: T }
  | { ok: false; error: E };
```

```ts
const r = await startBuild(deckId);
if (!r.ok) return r;          // the caller decides: retry, surface, fall back
watchBuild(r.value);
```

**Bugs throw.** A broken invariant, an unreachable branch, a parse on data that was supposed to be validated already. These are defects to fix, not conditions to handle. Let them throw, catch at the error boundary, and show human copy. Do not wrap a programmer error in a `Result`; that hides the bug behind a code path.

The line: *would a correct system ever produce this?* If yes, it is a `Result`. If no, it throws.

### Why not throw everything

Exceptions are invisible in a function signature. A function returning `Result<Deck>` tells the caller at compile time that it can fail, and the caller cannot forget. That is the whole reason expected failures are typed: the failures that actually happen are the ones you most need the compiler to force you to handle.

### Why not Result everything

Truly impossible states as Results means every call site handles a branch that can never run. That is verbose enough that, working solo, you would start ignoring it, and an ignored Result is worse than a thrown bug. Throwing keeps the impossible path out of the code you read every day.

## Generated types live in the repo

**Superseded 2026-09-26: there is no package to publish.** v3 shipped the generated schema as `@d-design/schema` to three TypeScript consumers, with Changesets bumps and npm trusted publishing. v4 has one consumer in the same repo, so the generated file is committed at `web/lib/api/schema.d.ts` and checked by the gate's no-diff step. No versioning, no publish job, no bumps. Revisit only if something outside this repo ever consumes the API's types.

## No enums, no classes for data

Use `const` objects and union types instead of TS `enum`, which emits runtime code and has surprising semantics. `erasableSyntaxOnly` above enforces this at the compiler, so nobody has to remember it.

Use plain typed objects and functions instead of classes for data: a `Deck` is data, not an object with methods. Classes are fine where identity and lifecycle genuinely matter, which is rare here. For everything else, write functions that transform typed data.
