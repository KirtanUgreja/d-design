# TypeScript

## Strict, and then stricter

`tsconfig` runs `strict: true` plus `noUncheckedIndexedAccess`. ESLint bans two things the compiler allows:

- **`any`** — use `unknown` and narrow, or type it properly. `any` deletes the compiler.
- **the non-null `!` operator** — it is a lie to the type system. If a value can be null, handle it; if it truly cannot, restructure so the type reflects that.

The compiler is the first and cheapest test. Most bugs that matter are the ones it already catches for free — the rules above stop you from switching it off one expression at a time.

## Types come from schemas, never written twice

Zod is the source of truth. Types are inferred.

```ts
// schema/scene.ts
export const Block = z.discriminatedUnion('type', [...]);
export type Block = z.infer<typeof Block>;   // derived, never hand-written
```

A hand-written type that duplicates a schema is a second source of truth that will drift. If you have a type and a validator for the same shape, the type is wrong — infer it.

## Trust boundaries: one parse, at entry

**Every external input is Zod-parsed exactly once, at the point it enters the system. Past that point it is typed and trusted.**

External means: HTTP request bodies, AI model output, uploaded file metadata, integration data (Airtable/Notion), and anything from the URL. All of it is `unknown` until parsed, and none of it is re-validated downstream.

```ts
// at the boundary
const brief = Brief.parse(rawInput);   // throws on bad shape — this is a bug path, see below
// everywhere after: brief is Brief, no re-checking
```

This mirrors the security model's trust boundaries exactly ([../security/README.md](../security/README.md)). Scattered re-validation is the anti-pattern: it drifts out of sync with the schema and hides where the real boundary is. One parse point per input, and the type carries the guarantee from there.

The AI pipeline is the boundary most easily forgotten — model output is internal plumbing but fully untrusted. It is parsed like any other external input.

## Errors: typed Results for the expected, throw for the impossible

Two categories, two mechanisms.

**Expected failures return a `Result`.** These are things that happen in normal operation: AI repair exhausted, quota reached, upload rejected, integration unreachable, validation failed on user input. The caller must handle them, and the compiler makes sure it does.

```ts
// lib/result.ts
export type Result<T, E = AppError> =
  | { ok: true; value: T }
  | { ok: false; error: E };
```

```ts
const r = await runBuild(outline);
if (!r.ok) return r;          // caller decides: retry, surface, fall back
useScene(r.value);
```

**Bugs throw.** A broken invariant, an unreachable branch, a `parse` on data that was supposed to be validated already — these are not conditions to handle, they are defects to fix. Let them throw, catch at the route boundary, log, return a 500. Do not wrap a programmer error in a `Result`; that hides the bug behind a code path.

The line: *would a correct system ever produce this?* If yes, it is a `Result`. If no, it throws.

### Why not throw everything

Exceptions are invisible in a function signature. A function returning `Result<Scene>` tells the caller it can fail, at compile time, and the caller cannot forget. That is the whole reason expected failures are typed — the failures that actually happen are the ones you most need the compiler to force you to handle.

### Why not Result everything

Truly impossible states as Results means every call site handles a branch that can never run. That is verbose enough that, solo, you would start ignoring it — and an ignored Result is worse than a thrown bug. Throwing keeps the impossible path out of the code you read every day.

## No enums, no classes for data

Use `const` objects and union types over TS `enum` (which emits runtime code and has surprising semantics). Use plain typed objects and functions over classes for data — a `Scene` is data, not an object with methods. Classes are fine where identity and lifecycle genuinely matter (rare here); for everything else, functions transforming typed data.
