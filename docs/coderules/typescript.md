# TypeScript

## Strict, and then stricter

`tsconfig` runs `strict: true` plus `noUncheckedIndexedAccess` and `erasableSyntaxOnly`. ESLint bans two things the compiler allows:

- **`any`** — use `unknown` and narrow, or type it properly. `any` deletes the compiler.
- **the non-null `!` operator** — it is a lie to the type system. If a value can be null, handle it; if it truly cannot, restructure so the type reflects that.

The compiler is the first and cheapest test. Most bugs that matter are the ones it already catches for free — the rules above stop you from switching it off one expression at a time.

`erasableSyntaxOnly` is worth calling out: it makes TS `enum`, `namespace`, and class parameter properties **compile errors**, which retires the `no-restricted-syntax` lint rule this project would otherwise need for the enum ban below. A compiler flag beats a lint rule — it is one line, it cannot be disabled per-file without it being obvious, and it runs first. It also keeps every `.ts` file valid input for Node's native type stripping, which costs nothing to preserve and occasionally saves a build step.

## Which TypeScript — and the one thing that breaks

**TypeScript 7.0** shipped 8 July 2026: the compiler rewritten in Go, generally 8–12× faster on full builds with roughly 18% less memory. Microsoft's own VS Code build went from 125.7s to 10.6s. It also flips `strict` and `esnext` on by default and turns TypeScript 6.0's deprecations into hard errors — which for this project means the defaults finally match what the rules already demanded.

A 10× typecheck is not a vanity number here. `tsc --noEmit` sits in the pre-commit gate ([tooling.md](tooling.md)), and a gate that returns in under a second is a gate you never route around.

**The catch, and it is a real one: TypeScript 7.0 ships without a public compiler API.** Anything that reads the type graph programmatically — `typescript-eslint` above all — cannot run on it. A stable API is planned for 7.1.

The documented interim pattern, and the one to use:

```jsonc
// package.json — TS 7 for the project, TS 6 pinned for the linter only
"devDependencies": {
  "typescript": "^7.0",
  "@typescript/typescript6": "npm:typescript@^6.0"   // typescript-eslint reads this
}
```

Typecheck runs on 7; type-aware lint runs on the pinned 6. It is two compilers on disk and one line of config, and it is temporary. Revisit when 7.1 lands the API — that is a ledger entry to delete, and deletion is a feature ([dependencies.md](dependencies.md)).

This is also the reason to be unhurried about it. Nothing in this project needs 7 on day one; the gate is fast enough on 6 for a codebase this size. Take it when the ecosystem has caught up, not because the number is large.

## Types come from schemas, never written twice

Zod is the source of truth. Types are inferred.

```ts
// schema/scene.ts
export const Block = z.discriminatedUnion('type', [...]);
export type Block = z.infer<typeof Block>;   // derived, never hand-written
```

A hand-written type that duplicates a schema is a second source of truth that will drift. If you have a type and a validator for the same shape, the type is wrong — infer it.

### The JSON Schema is derived too

This project has a second, less obvious place the same shape would be written twice. Structured outputs needs a **JSON Schema** to constrain generation ([../v1/ai-pipeline.md](../v1/ai-pipeline.md)); validation needs a **Zod schema** to parse the response. Two documents describing one shape, in different syntaxes, in different files, kept in sync by hand — the exact drift this rule exists to prevent, and the worst possible place for it. A JSON Schema that has quietly fallen behind the Zod schema means the model is constrained to generate the wrong thing, and you find out through a repair-rate creep rather than an error.

Zod 4 removes the problem: **`z.toJSONSchema()` is built in.** The Zod schema stays the single source of truth, the JSON Schema is generated from it at build time, and drift is not something to police.

```ts
// schema/scene.ts — the one definition
export const Scene = z.object({ /* ... */ });
export type Scene = z.infer<typeof Scene>;              // types derived
export const SCENE_JSON_SCHEMA = z.toJSONSchema(Scene); // model constraint derived
```

Zod 4 is the version to build on regardless: ~14× faster string parsing and a 57% smaller core bundle than v3, with `z.discriminatedUnion` validating in O(1) off the discriminator — which is exactly the shape `Block` is.

Two caveats to know before relying on it:

- **Keep a discriminated union off the schema root.** `toJSONSchema` output for a root-level `discriminatedUnion` has known rough edges with strict structured-output validators. Not a problem here — the root is an object (`Scene`/`Experience`) and `Block` is nested — but it is a constraint on how the schema is shaped, so it is written down rather than rediscovered.
- **Character caps still do not survive the trip.** Structured outputs does not support `minLength`/`maxLength`; the generated JSON Schema carries the *shape*, and Zod enforces the *lengths* after the response. That two-layer split is described in [../v1/scene-schema.md](../v1/scene-schema.md) and is unchanged by generating the schema — it just means one file now produces both layers.

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

**Tool-call arguments are the newest one, and the most deceptive.** A model calling `read_document({ id })` looks like a function call in your own code. It is not: the argument was produced by a model that may be reading an attacker's PDF ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)). Every tool parses its arguments with Zod at the tool boundary, and — because ownership is an authorization decision — a document id belonging to another account is a refusal that **fails closed** ([patterns.md](patterns.md)).

Server Actions have the same shape of trap for the same reason: they read as local calls and are public HTTP endpoints ([structure.md](structure.md)). **The rule generalizes to: if a value crossed a process boundary to get here, it is external, regardless of how local the call site looks.**

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

## The schema is a published package

`src/schema/` ships as **`@d-design/schema`** so the fetch worker can use it ([structure.md](structure.md)). That makes the most important shape in the system a versioned artifact, and versioned artifacts have their own discipline.

- **The app repo consumes the workspace source, not the published package.** Publishing exists for the *other* repo. If the app ever consumed the tarball, every schema change — which is most of v1 — would need a publish before it could be used.
- **Version bumps go through Changesets**, so a bump is a reviewed file in the PR that caused it rather than a decision made at publish time.
- **A breaking schema change is a major bump and the fetch worker is updated in the same session.** A pinned version drifting behind is the exact silent divergence a package was chosen to prevent ([../techstack/decisions.md](../techstack/decisions.md)); the pin only helps if someone reads it.

**Publish with npm trusted publishing (OIDC from GitHub Actions).** Short-lived credentials, no long-lived npm token in CI — one fewer permanent secret, and it removes the credential class that the registry compromises in [dependencies.md](dependencies.md) were built on.

One caveat worth knowing before relying on it: **provenance attestations are not generated for packages built from private repositories**, and this repo is private. Trusted publishing still works and still removes the token; the Sigstore attestation does not appear. That is acceptable for a package only you consume — it is worth knowing so nobody later assumes a verification step exists that does not.

## No enums, no classes for data

Use `const` objects and union types over TS `enum` (which emits runtime code and has surprising semantics). `erasableSyntaxOnly` above enforces this at the compiler, so it is not a rule anyone has to remember. Use plain typed objects and functions over classes for data — a `Scene` is data, not an object with methods. Classes are fine where identity and lifecycle genuinely matter (rare here); for everything else, functions transforming typed data.
