# TypeScript

The renderer half of the codebase — `web`, `render`, and the fetch worker. The backend is [python.md](python.md), and the two are held together by a codegen step that this document is now downstream of rather than the source of.

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

## Types come from the generated schema, never written twice

**Superseded.** This section used to say *"Zod is the source of truth."* It is not any more — **Pydantic is** ([python.md](python.md)), and both the TypeScript types and the Zod validator are generated from it into `@d-design/schema`.

```ts
// node_modules/@d-design/schema — GENERATED. Do not edit.
export const Block: z.ZodType<...>;   // generated validator
export type Block = ...;              // generated type
```

The rule that matters most is short: **never hand-edit generated code, and never hand-write a type that duplicates the generated one.** The gate regenerates and fails on a diff, so a hand-edit does not survive a commit — but it will look entirely reasonable in review, which is why it is stated here rather than left to the gate.

If you find yourself wanting a type the generated schema does not give you, that is a signal the Pydantic schema is missing something. **Change it there.** A local type alias for a generated shape is the first copy, and the first copy is where the drift starts.

### Why the editor still gets a Zod validator

Generating types alone would have been simpler and it was considered ([../techstack/decisions.md](../techstack/decisions.md)). The editor patches a block and revalidates the tree after every change (`v1/ai-pipeline.md`); routing that through the Python API would put a network round trip inside a keystroke-scale interaction and make the editor useless offline.

So a validator is generated too. It is **not** a second source of truth — it is the same source, compiled twice, and the round-trip test in [python.md](python.md) proves both agree on the same fixture — **for what JSON Schema can say.** Phase 01 built that test and it immediately drew the line: field-level shape (a length cap, an item count, a pattern) crosses the boundary; whole-tree structural rules ("exactly one hook and it is first," "ids unique within this list") do not, because JSON Schema validates one node's shape and has no vocabulary for a predicate over a whole tree. That is not an emitter gap to fix — it is what the format is. The nine rules of that shape stay Python-only, asserted at the pipeline boundary; the five that are field-level generate into Zod and are what the editor actually needs, since `BlockPatch` — the only offline write path — touches one block's props and cannot violate a whole-tree rule regardless (`v1/plan/01-scene-schema.md` → "Built").

Zod 4 remains the version to build on: ~14× faster string parsing and a 57% smaller core bundle than v3, with `z.discriminatedUnion` validating in O(1) off the discriminator — which is exactly the shape `Block` is.

Three caveats survive the change of source and are worth knowing before relying on them:

- **The discriminated union stays off the schema root.** `Scene`/`Experience` is an object and `Block` is nested inside it. Root-level tagged unions have known rough edges with strict structured-output validators, so this is a constraint on how the Pydantic schema is written, enforced by convention on the other side of the boundary.
- **Character caps do not survive the trip to the model.** Structured outputs widely ignores `minLength`/`maxLength`. The generated JSON Schema carries the *shape*; Pydantic enforces the *lengths* on the response (`v1/scene-schema.md`). The generated Zod carries them too, which is what lets the editor reject an over-long headline without asking the server.
- **A cross-field rule worth having offline is worth rewriting as a field-level one.** `CTA.href`'s scheme allowlist was a `model_validator` — correct, but Python-only, and the property panel patches `href` directly. Rewritten as a `Field(pattern=...)`, it generates into Zod's `.regex()` and the editor now rejects a pasted `javascript:` URL without a round trip. Not every cross-field rule can make this move — most need real cross-field or cross-array reasoning a pattern cannot express — but check before assuming a rule has to stay Python-only.

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

The generated output ships as **`@d-design/schema`** so `web`, `render`, and the fetch worker can use it ([structure.md](structure.md)). That makes the most important shape in the system a versioned artifact, and versioned artifacts have their own discipline.

**With one repo per runtime, every TypeScript consumer now takes the published package** — there is no workspace shortcut left. That is a real cost the Python move added: a schema change is a generate, a publish, and three bumps, where it used to be a file edit.

- **Version bumps go through Changesets**, so a bump is a reviewed file in the PR that caused it rather than a decision made at publish time.
- **A breaking schema change is a major bump, and every consumer is updated in the same session.** A pinned version drifting behind is the exact silent divergence a package was chosen to prevent ([../techstack/decisions.md](../techstack/decisions.md)); the pin only helps if someone reads it.
- **During v1 this is friction with no payoff yet**, because there is one consumer and the schema changes constantly. A local file link is the right shortcut, marked `ponytail:` with the trigger — the second TypeScript consumer, which arrives with `render` in v2.

**Publish with npm trusted publishing (OIDC from GitHub Actions).** Short-lived credentials, no long-lived npm token in CI — one fewer permanent secret, and it removes the credential class that the registry compromises in [dependencies.md](dependencies.md) were built on.

One caveat worth knowing before relying on it: **provenance attestations are not generated for packages built from private repositories**, and this repo is private. Trusted publishing still works and still removes the token; the Sigstore attestation does not appear. That is acceptable for a package only you consume — it is worth knowing so nobody later assumes a verification step exists that does not.

## No enums, no classes for data

Use `const` objects and union types over TS `enum` (which emits runtime code and has surprising semantics). `erasableSyntaxOnly` above enforces this at the compiler, so it is not a rule anyone has to remember. Use plain typed objects and functions over classes for data — a `Scene` is data, not an object with methods. Classes are fine where identity and lifecycle genuinely matter (rare here); for everything else, functions transforming typed data.
