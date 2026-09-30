# Python

The backend language. As of 2026-09-26, `api` owns **the engine, every model call, all data and the export** ([../v4/engine.md](../v4/engine.md), [../techstack/backend.md](../techstack/backend.md)). The UI half is [typescript.md](typescript.md). The two meet only at the HTTP API, and the section below on how that API's shapes reach TypeScript is the one to read first.

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
- **No `# type: ignore` without a code and a reason on the same line.** `# type: ignore[import-untyped]  # nh3 ships no stubs` is fine. A naked ignore is the non-null `!` wearing a different hat.
- **No `cast()` to make an error go away.** A cast is a claim you are making on the checker's behalf. If it is wrong, it is wrong silently and forever.

**Ruff** for lint and format: one tool, one config block, and it replaces the flake8/isort/black stack outright. Format is not a decision, the same way Prettier is not one on the other side.

> The point of the pairing is that the two languages have the *same* rules, not similar ones. A reviewer moving between `api/` and `web/` should not have to reload a different set of standards, and neither should the model writing most of this.

## Pydantic is the source of truth

**Rewritten 2026-09-26.** Every shape that crosses a boundary is a Pydantic model:
- the engine's models (`Brief`, `Fact`, `SlidePlan`, `Storyline`, `Theme`, `Slide`, `Deck`, `CostLedger`; [../v4/engine.md](../v4/engine.md) → "Data model")
- every route's request and response

Everything else is derived:

```
api/engine/models.py + route request/response models      ← hand-written, the one definition
   │
   ├─ Model.model_json_schema()  ─▶ the structured-output constraint for JSON-mode calls
   │                                 (in-process, never travels)
   │
   └─ FastAPI ─▶ openapi.json ─▶ openapi-typescript ─▶ web/lib/api/schema.d.ts   (GENERATED)
```

Three rules make the generated half safe. Each is enforced, not remembered:

**1. Generated TypeScript is never hand-edited.** The generated file carries a header saying so. The gate regenerates it from the app's OpenAPI document and fails if the output differs from what is committed. A hand-edit is drift arriving through the only door left open, and it will look like a perfectly reasonable small fix in review.

**2. The JSON Schema never becomes a file someone maintains.** `model_json_schema()` is called where the seam needs it. The model call happens in Python, so the constraint has nowhere to travel to and no chance to go stale.

**3. A shape change is one commit that touches both sides**: the Pydantic model and the regenerated types. If regeneration lands in a follow-up, the two have already drifted, and the window is as long as the review queue.

**What this replaced, and why.** v3 generated TypeScript types *and a Zod validator* for the whole `Deck` tree into a published `@d-design/schema` package. It needed them because a TypeScript renderer and an offline editor consumed that tree. v4 has no TypeScript renderer: slides are HTML the engine assembles. So `web` needs only the API's payload types, and OpenAPI is how FastAPI already publishes them. Three things went with the v3 approach:
- the package and its publishing
- the Changesets bumps
- the cross-language fixture round-trip

### Slide HTML is not a schema

Slide HTML is the one piece of model output that is not JSON. Compose, repair and revise calls answer in text mode: `<slide>…</slide><style>…</style>`. HTML escaped inside JSON strings wastes tokens and breaks, so it never travels as JSON ([../v4/engine.md](../v4/engine.md) → "The model seam").

It has a **contract** instead of a schema:
- a fragment plus its CSS, scoped by a Declarative Shadow DOM root per slide (the lint does not rewrite selectors)
- content nodes tagged `data-field`
- component slots (`data-chart`, `data-image`); no icons and no `<a>` links in v4

It is parsed, sanitized (`nh3`) and linted (`tinycss2`) at entry, exactly once ([../v4/design-engine.md](../v4/design-engine.md)). Past that point it is trusted like any other parsed value. A lint failure is an expected failure, so it returns a `Result` whose error names the violation, and that error becomes the repair prompt.

### The constraints that do not survive the trip

| | |
|---|---|
| **Shape**: fields, types, discriminators | Carried by the JSON Schema. Enforced by Pydantic on the response; the decoder only shifts the odds |
| **Character and word caps**: headline ≤12 words, ≤3 points | **Do not survive.** Structured-output implementations widely ignore `minLength`/`maxLength`. Keep them on the Pydantic field anyway, because they cost nothing and they do the rejecting. Also state every budget in the prompt as a hard number: prompting is the only portable lever on length. (v3's schema allowed 500 characters where its prompt said 60, so the cap on the field was the real rule, not the prompt) |
| **Semantic rules**: an assertion headline, a source for every number, notes on every slide | Pydantic validators, plus the content evals ([../v4/content.md](../v4/content.md)) |

**Keep a discriminated union off the schema root.** A `SlidePlan` holds its optional `stat`, `quote` and `chart` parts inside an object. That is the shape strict structured-output validators handle cleanly. It is a constraint on how the schema is written, so it is written down rather than rediscovered.

## Trust boundaries: one parse, at entry

**Every external input is parsed exactly once, at the point it enters the system. Past that point it is typed and trusted.**

External means all of these, and all of them are untyped until parsed and never re-validated downstream:
- HTTP request bodies
- **model output**, both JSON and slide HTML
- web-search results and their citations
- anything a user pasted
- anything from the URL

```python
brief = Brief.model_validate(raw)     # at the boundary; raises, which is a bug path
# everywhere after: brief is Brief, no re-checking
```

Two of those are the ones actually forgotten:

- **Model output is internal plumbing and fully untrusted.** It is parsed like any other external input. This is not a formality: it is the gate the security posture rests on ([../security/prompt-injection.md](../security/prompt-injection.md)). For slide HTML, "parsed" means sanitized and linted too, because the output channel is now markup.
- **Search results look like our own data and are not.** A page returned through `openrouter:web_search` can carry instructions aimed at the model. It becomes a `Fact` at entry, quoted in prompts as data, never followed. The model has no tool with side effects ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)), so an injected "do X" has nothing to do X with.

**The rule generalizes: if a value crossed a process boundary to get here, it is external, however local the call site looks.** The API between `web` and `api` is such a boundary in both directions.

## Errors: typed Results for the expected, raise for the impossible

Same split as TypeScript ([typescript.md](typescript.md)), which is the point: the rule should not change when the language does.

**Expected failures return a `Result`.** These happen in normal operation:
- repair exhausted
- a slide that still fails QA after the repair ladder
- an image the image model did not produce
- research that returned nothing usable
- a lint violation
- the budget cap reached (phase 29)

Python has no union types in the TypeScript sense, so this is a small tagged pair:

```python
# lib/result.py
type Result[T, E = AppError] = Ok[T] | Err[E]
```

`mypy --strict` makes the match exhaustive, so a caller that forgets a branch fails the gate. That is the property being bought. Without a strict checker, `Result` in Python is just ceremony, which is why the strict rule above is a prerequisite for this one rather than a neighbour.

**One failed slide is a `Result` on that slide, never an exception that unwinds the deck.** v3's build threw away every finished slide when one failed (`slide_builder.py:116`), so v4 makes the per-slide `Result` the unit.

**Bugs raise.** A broken invariant, an unreachable branch, a `model_validate` on data that was supposed to be validated already. Let them raise, catch at the route boundary, log, and return a 500 whose body is human copy, never the exception text.

The line is one question: *would a correct system ever produce this?* If yes, `Result`. If no, raise.

**Never `except Exception: return <permissive default>`.** That is [patterns.md](patterns.md) rule 5 in its most common Python spelling, and it reads as defensive programming right up until it is the incident.

## Async, and the one thing that bites

`api` is async end to end: FastAPI, `httpx.AsyncClient`, Playwright's async API, and SQLAlchemy's async session from phase 29. The pipeline is I/O bound by definition: it waits on model calls and on a browser.

**One blocking call in an async handler blocks the whole event loop.** The symptom is latency on unrelated requests, which is the hardest kind of bug to attribute. A sync library goes in `run_in_threadpool`, or it does not go in `api` at all. The v3 seam was synchronous and ran in a thread, and that is why its slides were built one after another.

Specifics worth knowing before they cost an afternoon:

- **One `httpx.AsyncClient`, module-level, reused.** A client per request leaks connections and loses keep-alive on the hot path, and the model seam is the hot path ([performance.md](performance.md)).
- **Parallel slides go through one semaphore**, never through `gather` over an unbounded list. Five in flight is the v4 default ([../v4/engine.md](../v4/engine.md)); an unbounded fan-out turns a 20-slide deck into a rate-limit incident.
- **One browser, launched once, with a small page pool, in the worker process.** A Chromium launch per slide costs more than the measurement it serves. From phase 27 the API process never starts a browser or calls a model; `api/worker.py` does ([structure.md](structure.md)).
- **`asyncpg` caches prepared statements** (phase 29), which breaks behind a transaction-mode pooler ([../techstack/backend.md](../techstack/backend.md)). Disable the cache; the errors it produces otherwise look like nothing else in the system.

## No classes for data

Pydantic models and dataclasses for data; functions that transform them for behaviour. A `Deck` is data, not an object with methods.

Classes are fine where identity and lifecycle genuinely matter: a client, a browser pool, a context manager. They are not a namespace. A class whose methods never touch `self` is a module with extra syntax.

This is the same rule as [typescript.md](typescript.md)'s "no classes for data", and it matters more in Python because the language makes the wrong version so comfortable.

## Test

**pytest.** What gets tested is deliberately narrow ([ai-authorship.md](ai-authorship.md)):

- [ ] **The seam**: the repair path (the real previous answer goes back), `finish_reason` handling, and one cost-ledger entry per call
- [ ] **The sanitizer** against an XSS corpus, and **the lint** against banned CSS: each fixture must be rejected, not merely warned
- [ ] **The QA metrics** against fixture slides with known overflow, collision and contrast defects
- [ ] **The export** opened from `file://` in a real browser, with zero network requests
- [ ] **Regenerating the OpenAPI types produces no diff**: the gate rule, as a test
- [ ] **The file store's single-writer rule**: an API edit while a job is generating returns 409
- [ ] **Every fail-closed check** proven by making it raise
- [ ] **From phase 29:** the tenant wrapper's unset case fails rather than matching everything ([patterns.md](patterns.md) rule 4)

The browser-backed tests carry a `browser` marker. They run in CI and before a phase exits, and are kept out of the per-commit gate so it stays fast ([tooling.md](tooling.md)).

No coverage threshold. The ponytail rule holds: one runnable check per non-trivial branch, none for trivial code.
