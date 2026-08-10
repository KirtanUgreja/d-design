# Python

The backend language — `api` and `jobs` ([../techstack/backend.md](../techstack/backend.md)). The renderer half of the codebase is [typescript.md](typescript.md), and the two are held together by the schema codegen below, which is the most important section in this file.

## Strict, and what that means here

Python's default is permissive, so strictness is configuration rather than a property of the language. All of it lives in `pyproject.toml`, so there is one place to read it and one place it can be weakened visibly.

```toml
[tool.mypy]
strict = true
warn_unreachable = true
disallow_any_explicit = true          # `Any` is a decision, not a shrug
```

Three rules on top of `strict = true`, each the Python spelling of a TypeScript non-negotiable:

- **No bare `Any`.** Use a protocol, a union, or `object` and narrow. `Any` deletes the checker exactly the way TS `any` does.
- **No `# type: ignore` without a code and a reason on the same line.** `# type: ignore[arg-type]  # asyncpg stubs lag` is fine; a naked ignore is the non-null `!` wearing a different hat.
- **No `cast()` to make an error go away.** A cast is a claim you are making on the checker's behalf. If it is wrong, it is wrong silently and forever.

**Ruff** for lint and format — one tool, one config block, and it replaces the flake8/isort/black stack outright. Format is not a decision, the same way Prettier is not one on the other side.

> The point of the pairing is that the two languages have the *same* rules, not similar ones. A reviewer moving between `api/` and `web/` should not have to reload a different set of standards, and neither should the model writing most of this.

## The schema is the source of truth

**This is the load-bearing section of the Python move.** [../techstack/decisions.md](../techstack/decisions.md) records why it exists; this is how it works.

Pydantic owns the `Scene` shape. Everything else is generated from it.

```
schema/scene.py           ← the one definition, hand-written
   │
   ├─ Scene.model_json_schema()   ─▶ the model's structured-output constraint
   │                                  (in-process, never travels)
   │
   └─ CI ─▶ JSON Schema ─▶ TypeScript types
                        ─▶ a Zod validator
                             │
                             └─▶ @d-design/schema  ─▶ web · render · fetch worker
```

Three rules make the generated half safe. Each is enforced, not remembered:

**1. Generated TypeScript is never hand-edited.** Every generated file carries a header saying so, and the gate runs the generator and fails if the output differs from what is committed. A hand-edit is the drift arriving through the only door left open — and it will look like a perfectly reasonable small fix in review.

**2. The JSON Schema never becomes a file someone maintains.** `model_json_schema()` is called at the point the seam needs it. The model call happens in Python, so the constraint has nowhere to travel to and no chance to go stale. This is the one thing that got *simpler* with the move: the old design had to generate a JSON Schema from Zod and keep it in step; now the schema and the caller are in the same process.

**3. A schema change is one commit touching both languages.** If regeneration lands in a follow-up PR, the two have already drifted, and the window is exactly as long as the review queue.

### The constraints that do not survive the trip

Unchanged in substance from the Zod-first design, restated because the mechanism moved:

| | |
|---|---|
| **Shape** — fields, types, discriminators | Carried by the generated JSON Schema. Enforced by Pydantic on the response; the decoder only shifts the odds (`v1/ai-pipeline.md`) |
| **Character caps** — `Headline ≤ 60`, `Body ≤ 240` | **Do not survive.** Structured-output implementations widely ignore `minLength`/`maxLength`. Keep them on the Pydantic field anyway — they cost nothing and they are what does the rejecting — and state every budget in the prompt as a hard number, because prompting is the only portable lever on length |
| **Semantic rules** — one `Headline` per scene, region validity, claim provenance | Pydantic validators plus the post-build checks |

**Keep a discriminated union off the schema root.** `Block` is a tagged union and it is nested inside `Scene`, which is an object — that is the shape strict structured-output validators handle cleanly. It is a constraint on how the schema is written down rather than a limitation, so it is written down rather than rediscovered.

## Trust boundaries: one parse, at entry

**Every external input is `model_validate`'d exactly once, at the point it enters the system. Past that point it is typed and trusted.**

External means: HTTP request bodies, **model output**, tool-call arguments, uploaded file metadata, integration data, and anything from the URL. All of it is untyped until parsed, and none of it is re-validated downstream.

```python
brief = Brief.model_validate(raw)     # at the boundary — raises, which is a bug path
# everywhere after: brief is Brief, no re-checking
```

Two of those are the ones actually forgotten:

- **Model output is internal plumbing and fully untrusted.** It is parsed like any other external input. This is not a formality — it is the gate the entire security posture rests on ([../security/prompt-injection.md](../security/prompt-injection.md)).
- **Tool-call arguments look like your own function calls and are not.** A model calling `read_document(id=7)` may be reading an attacker's PDF ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)). Parse at the tool boundary, and check ownership there — and because ownership is an authorization decision, it **fails closed** ([patterns.md](patterns.md) rule 5).

**The rule generalizes: if a value crossed a process boundary to get here, it is external, regardless of how local the call site looks.** With five runtimes there are more such boundaries than there used to be, and the API surface between `web` and `api` is the newest one.

## Errors: typed Results for the expected, raise for the impossible

Same split as TypeScript ([typescript.md](typescript.md)), which is the point — the rule should not change when the language does.

**Expected failures return a `Result`.** Repair exhausted, quota reached, upload rejected, integration unreachable, session invalid. Python has no union types in the TypeScript sense, so this is a small tagged pair:

```python
# lib/result.py
type Result[T, E = AppError] = Ok[T] | Err[E]
```

`mypy --strict` makes the match exhaustive, so a caller that forgets a branch fails the gate. That is the property being bought, and without a strict checker `Result` in Python is just ceremony — which is why rule 1 above is a prerequisite for this one rather than a neighbour.

**Bugs raise.** A broken invariant, an unreachable branch, a `model_validate` on data that was supposed to be validated already. Let them raise, catch at the route boundary, log, return a 500.

The line is one question: *would a correct system ever produce this?* If yes, `Result`. If no, raise.

**Never `except Exception: return <permissive default>`.** That is [patterns.md](patterns.md) rule 5 in its most common Python spelling, and it reads as defensive programming right up until it is the incident.

## Async, and the one thing that bites

`api` is async end to end — FastAPI, SQLAlchemy's async session, `httpx.AsyncClient`, PGQueuer. The pipeline is I/O bound by definition: it waits on model calls.

**One blocking call in an async handler blocks the whole event loop**, and the symptom is latency on unrelated requests, which is the hardest kind of bug to attribute. A sync library goes in `run_in_threadpool` or it does not go in `api` at all.

Two specifics worth knowing before they cost an afternoon:

- **`asyncpg` caches prepared statements**, which breaks behind a transaction-mode pooler ([../techstack/backend.md](../techstack/backend.md)). Disable the cache; the errors it produces otherwise look like nothing else in the system.
- **One `httpx.AsyncClient`, module-level, reused.** A client per request leaks connections and loses keep-alive on the hot path — and the model seam is the hot path ([performance.md](performance.md)).

## No classes for data

Pydantic models and dataclasses for data; functions that transform them for behaviour. A `Scene` is data, not an object with methods.

Classes are fine where identity and lifecycle genuinely matter — a client, a connection pool, a context manager. They are not a namespace. A class whose methods never touch `self` is a module with extra syntax.

This is the same rule as [typescript.md](typescript.md)'s "no classes for data", and it matters more in Python because the language makes the wrong version so comfortable.

## Test

**pytest**, and what gets tested is unchanged and deliberately narrow ([ai-authorship.md](ai-authorship.md)): the schema round-trip, the golden-brief pipeline run, the seam's repair and refusal paths, the tenant wrapper's unset case, and every fail-closed check proven by making it raise.

Three that only exist because of the language split, and all three are cheap:

- [ ] **Regenerating `@d-design/schema` from Pydantic produces no diff.** The gate rule, as a test
- [ ] **A `Scene` fixture round-trips through both validators** — Pydantic and the generated Zod — with the same verdict on the same input. This is what would actually catch a codegen bug
- [ ] **`current_setting('app.user_id')` on a connection where it was never set fails**, rather than matching everything ([patterns.md](patterns.md) rule 4)

No coverage threshold. The ponytail rule holds: one runnable check per non-trivial branch, none for trivial code.
