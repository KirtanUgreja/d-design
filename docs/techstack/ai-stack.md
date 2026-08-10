# AI Stack

Which models, chosen how, measured with what — and why there is no agent framework.

## The stance: no favourite model

**This product should not have a preferred model vendor.** It has a preferred *interface*: a call that takes a prompt and a JSON Schema and returns conforming JSON. Everything behind that is replaceable, and the choice of what sits there is an empirical question with a different answer per phase and a different answer every few months.

That is why [backend.md](backend.md) puts OpenRouter behind a thin seam rather than picking a vendor. The seam is not indecision — it is the recognition that any model named in this document will be wrong within two quarters, and that the thing worth building is the apparatus for switching rather than the conviction about which one.

**The corollary is that opinions are worthless here and measurements are not.** A model is chosen for a phase because it scored better on your briefs, not because of a benchmark, a launch post, or a reputation. The eval harness below is what makes that sentence actionable; without it, "provider-neutral" just means "picks whatever was in the last blog post."

## The landscape, August 2026

Stated so the seam has something concrete to be neutral about, not as a recommendation. All of it is stale on arrival.

| Tier | Examples | Rough input/output per MTok |
|---|---|---|
| **Frontier** | Claude Mythos Preview · Claude Opus 5 · GPT-5 family · Gemini 3 Pro · Grok 4 · GLM-5 | ~$2.50–$10 / ~$15–$50 |
| **Mid** | Claude Sonnet 4.6 · GPT-5.4 · Kimi K3 | ~$2.50–$3 / ~$15 |
| **Budget** | DeepSeek V3.2 (~$0.14/$0.28) · Qwen3.7 Flash (~$0.03/$0.13) | cents |
| **Open weights, self-hostable** | Llama · Qwen · DeepSeek · GLM | infrastructure cost only |

Two structural notes that outlast the specific names:

- **Vision is no longer scarce.** ~67 models have vision, and **28 of those are open-weight and self-hostable**. Art-direction derivation (`v2/art-direction-engine.md`) is not gated on a single vendor.
- **Pricing models are diverging.** Some providers are moving from token meters to task quotas (Kimi Code bills 300–1,200 calls per 5-hour window). Cost accounting that assumes per-token billing will eventually mismeasure. Log both calls and tokens.

## What actually constrains the choice here

Benchmarks are close to useless for this product because none of them measure the thing it needs. Four criteria do, in order:

**1. Schema conformance rate.** The Build phase emits a `Scene` tree that must satisfy Pydantic. The metric is the **repair rate**, and it is the single number that determines whether a model is usable here. A model that scores brilliantly on reasoning and emits a malformed union discriminator 8% of the time is worse for this job than a cheaper model that never does.

Under OpenRouter this matters more than it would with decoder-enforced structured outputs, because enforcement varies by provider ([decisions.md](decisions.md)). Measure it per model *and per route*.

**2. Design judgment under constraint.** Build does not write CSS — it chooses layout, emphasis, motion intent, and copy that fits a character budget. That is a taste-and-constraint task, and it correlates poorly with coding or math benchmarks. **The only way to know is to look at rendered output.**

**3. Vision quality, for v3 only.** AD derivation and the visual verification loop ([pipeline-tools.md](pipeline-tools.md)) need a model that reads type character, density, and spatial rhythm from an image. Distinct capability, distinct evaluation, possibly a distinct model.

**4. Cost, last.** At roughly $0.20 per experience (`v1/ai-pipeline.md`), token cost is not this product's constraint and never has been. Cost matters for the *cheap* phases — Director, Intake, Edit run often and are structurally simple — and it is close to irrelevant for Build, where quality is everything.

> The one-line rule: **spend on Build, economise everywhere else, and let evals decide where the line falls.**

### The constraint none of the four predicted: reasoning tokens are billed out of `max_tokens`

Found live in v1, and it is a property of the *route* rather than of any model's quality, which is why none of the criteria above would have caught it.

**Every model behind this seam is a reasoning model, and OpenRouter bills hidden reasoning tokens out of the same `max_tokens` budget as the visible completion.** A trivial forty-word request burned 256 reasoning tokens and hit `finish_reason: length` having produced nothing. On Build — open-ended, and the phase with the largest output — reasoning silently ate a variable and sometimes large slice of the budget, so the completion was truncated, invalid, and repaired. Each repair is another full-length call.

Two things about the lever, both verified live rather than read:

- **`reasoning.max_tokens` does not cap it.** Set to 50, the model still spent 256 and produced nothing
- **`reasoning.effort: "minimal"` does.** Same run, 0 reasoning tokens, full completion

**The cost of getting this wrong was almost entirely wall-clock, not money**, which is why "cost, last" did not surface it. A call that runs to the token ceiling is the slowest call the provider can serve, and a truncated call buys a second one. The CI eval job — the same 12 cases, sequential, before and after the fix:

| | before | after |
|---|---|---|
| total model latency | 2,653 s | 250 s |
| slowest single case | 379 s | 93 s |
| scenes produced | 39 | 42 |
| errors | 10 | 7 — and all 7 are the injection corpus's controls firing correctly |

**Ten times faster, with better output.** The eval step went from 45m 49s to 5m 53s and took the whole `api` job from 47 minutes to 7 with no other step changing.

The generalisable rule: **when a route bills hidden tokens out of the visible budget, latency and repair rate are the same problem wearing two faces.** Instrument both, and treat a rising repair rate as a possible budget problem before assuming it is a model-quality one.

## Evals — the missing apparatus

This is the real gap the model question exposes. Model-neutrality without evals is not a strategy.

**v1 already specifies the dataset and does not call it one.** `v1/spec.md`'s verification step — *"5 golden briefs → run Director + Build → assert 100% schema-valid output"* — is a golden dataset. Growing it into a proper eval set is the highest-leverage AI work in the project after the renderer itself.

### The three layers

| Layer | What it does | When it runs |
|---|---|---|
| **Structural assertions** | Valid `Scene` JSON · no presentational values · every `CTA.href` traces to the Brief · budgets respected | Every PR. **Hard pass/fail** |
| **Quality scoring** | Rendered output judged on layout variety, copy fidelity to the Brief, motion appropriateness | Nightly, tracked as a trend |
| **Production tracing** | Repair rate, cost, latency, refusal rate per phase and per model | Continuously |

Layer 1 is deterministic and belongs in CI, gating merges. Layer 2 is probabilistic and must **never** gate a merge — a flaky judge blocking a deploy is how teams learn to skip the gate. Track the trend; investigate a drop.

The distinction matters because it mirrors the injection-suite rule already in [../security/testing.md](../security/testing.md): *structural assertions are absolute; probabilistic ones measure a rate*. Same idea, different failure.

### Tooling

**Promptfoo** for CI-gated structural evals — declarative YAML, runs locally and in Actions, no vendor. It is the most widely adopted open-source red-teaming and eval tool, which also means the injection corpus from [../security/testing.md](../security/testing.md) can live in the same harness as the quality evals. One tool, two jobs.

It is a Node CLI driving a Python API, which is fine — it calls the pipeline over HTTP like any other client, and a declarative eval file is worth more than language symmetry. If that ever grates, `promptfoo`'s Python provider hook is the escape hatch, not a rewrite.

**Langfuse** for tracing, prompt versioning, and building datasets *from production traces* — self-hostable, so prompts and outputs never leave your infrastructure. That last property is not a preference: [../security/tenancy-and-data.md](../security/tenancy-and-data.md) forbids storing prompts or outputs, because a prompt here is a customer's unreleased launch messaging under embargo. **A hosted eval platform that ingests full traces is in direct conflict with that rule.**

Self-hosted Langfuse resolves it, and only if traces are scrubbed and retained deliberately. **Do not adopt a trace-ingesting tool without deciding what it stores first** — this is the same failure as the Sentry configuration in [backend.md](backend.md), with a larger blast radius because tracing captures prompts by design rather than by accident.

**Prompts are versioned artifacts.** A prompt change is a behavior change with no type system behind it — it should be reviewable in a diff, tied to eval results, and rollback-able. In the repo, not in a database, so it moves through the same gate as the code.

## Language: Python for the backend, TypeScript for the renderer

**Superseded.** An earlier version of this document argued for TypeScript everywhere. The backend is now **Python (FastAPI)** and the reasoning is recorded in [decisions.md](decisions.md) → "The Python backend move". What follows is the state after that decision, not the argument for it.

| | Language | Why it is there |
|---|---|---|
| **api** — the four phases, data, quotas, jobs | **Python** | Where the pipeline and the model seam live |
| **web** — editor, renderer components, auth | **TypeScript** | The renderer is React. It cannot be anything else |
| **render** — scene tree → HTML, the visual loop | **TypeScript** | It is the renderer, running headless |
| **fetch worker** — hostile input | **TypeScript** | Unchanged. Keeps `unpdf`/`pdf.js` and Playwright as chosen |

**The renderer is why this is not a single-language project and never can be.** It is React, it runs in the browser editor *and* in the publish process, and [../coderules/patterns.md](../coderules/patterns.md) rule 2 requires exactly one implementation of it. A Python renderer would be a second implementation, which is the one thing that rule exists to prevent.

### The `Scene` schema, which is the whole cost of this move

The old argument against Python was precise and it was correct: *a Python service would need Pydantic models mirroring the Zod schema — a second definition of the most important shape in the system.* That objection has not been answered by being ignored. It has been answered by **making the second definition a build artifact instead of a file someone maintains.**

```
schema/  (Pydantic — the source of truth)
   │
   ├── model_json_schema()  ──▶  the model's structured-output constraint  (in-process, Python)
   │
   └── CI: Pydantic ─▶ JSON Schema ─▶ TS types + a generated Zod validator
                                          │
                                          └──▶ @d-design/schema  ──▶ web · render · fetch worker
```

Three rules make that safe, and all three are enforceable rather than remembered:

- **Generated TypeScript is never hand-edited.** It carries a generated-file header, and the gate fails if regenerating it produces a diff. A hand-edit to generated code is the drift, arriving by the only door left open.
- **The Pydantic schema and the JSON Schema are the same object**, produced by `model_json_schema()` at the point the seam needs it. Python is where the model call happens, so the constraint no longer travels.
- **A schema change is one commit that touches both languages.** If the regeneration is a separate PR, the two have already drifted.

**This is strictly worse than one language and it is worth being honest about that.** It buys the drivers that motivated the move — the Python AI/ML ecosystem, authoring fluency, a backend that is not a frontend framework's server half, and room for Python-shaped services later — and it costs a codegen step that must never be allowed to become optional.

### The guardrail that disappeared

This is the consequence most likely to bite, and it has nothing to do with schemas.

> **"It would be a second language" was doing real work.** It is what kept DSPy, LangGraph, CrewAI, and Pydantic AI out of this project without anyone having to argue against them. That barrier is gone. All of them are now one `pip install` away, in the process that holds database credentials.

So every rule that was previously enforced by friction now has to be enforced on purpose. That is what the next two sections are.

### DSPy — now native, and still offline

The old claim that DSPy *"has no real TypeScript equivalent"* was already going stale: [`ax-llm/ax`](https://github.com/ax-llm/ax) is the de-facto TypeScript port and ships GEPA, the reflective Pareto optimizer. That correction is now moot — the pipeline is Python, so DSPy and GEPA are native.

**The trigger is unchanged and the shape of the answer is unchanged:**

> **When:** a golden dataset of 50+ briefs with quality scores exists, and you are spending real time hand-tuning the Build prompt against it.
>
> **What:** DSPy runs **offline** and its output is a **prompt artifact committed to the repo**, reviewed in a diff like every other prompt ([../coderules/tooling.md](../coderules/tooling.md)). It is never imported by the running API.

Being in the same language is not a reason to make it a runtime dependency. It is the reason that rule now has to be written down.

## Agent framework: none

LangGraph, CrewAI, Pydantic AI, the OpenAI Agents SDK, Microsoft Agent Framework, Mastra — all mature, several genuinely good, and **none of them belong here.** The decision predates the Python move and survives it. It now rests on three legs instead of one.

### Leg 1 — this pipeline is not an agent

The four phases are a fixed sequence decided by your code, with a human gate in the middle:

```
Intake ──▶ Director ──▶ [human approves outline] ──▶ Build ──▶ Edit
```

No autonomous planning, no dynamic tool selection, no multi-agent negotiation, no memory across runs, no self-directed loops. An agent framework's entire value is orchestrating decisions the model makes about *what to do next* — and here your code makes every one of them. Adopting one would mean expressing four sequential function calls as a graph, adding a dependency, a state model, and a debugging surface, and buying nothing.

This is also why most of the OWASP Agentic Top 10 does not apply ([../security/adversarial-ai.md](../security/adversarial-ai.md)). **The absence of a framework is the same fact as the absence of the risk class.**

### Leg 2 — it would be a runtime-privileged dependency, and this class is being exploited

*(researched August 2026)*

[../coderules/dependencies.md](../coderules/dependencies.md) already has the rule that decides this: **where a dependency runs is part of the decision.** Hostile-byte parsers go in the fetch worker, which has no database, no VPC route, and one narrowly-scoped secret. An agent framework goes in the opposite place — the **api** process, which holds database credentials, model credentials, and (from v3) decrypted integration tokens.

That placement would be acceptable if the class were quiet. It is not:

| | |
|---|---|
| **CVE-2025-68664 "LangGrinch"** | CVSS **9.3** in `langchain-core`. Unescaped `lc` keys in `dumps()`/`dumpd()` on user-controlled dictionaries — leads to environment-secret disclosure, including API keys |
| **CVE-2026-34070** | Arbitrary filesystem read via LangChain |
| **CVE-2025-67644** | SQL injection in LangGraph's SQLite checkpointer (CVSS 7.3) |
| **CVE-2026-28277** | Unsafe msgpack deserialization in LangGraph — object reconstruction triggered by *loading a checkpoint* (CVSS 6.8) |
| **LangGraph flaw chain, June 2026** | Remote code execution against self-hosted agent deployments |
| **CVE-2026-25253 / ClawHavoc** | RCE in an agent *skill runtime*; within days, 1,200+ malicious skills were pushed to its marketplace |

The Cloud Security Alliance published a research note in March 2026 on agentic-framework CVEs **under active exploitation**. Read the list by shape rather than by vendor — checkpoint deserialization, state serialization, and skill/plugin loading are where the bugs are, and every framework in the category has all three.

The point is not that LangChain is uniquely bad; it is the most-used and therefore the most-audited, which is why its CVEs are the ones with names. **The point is that adopting any of them puts a large, fast-moving, actively-targeted dependency in the one process that has something worth stealing** — to orchestrate four function calls that are already in the right order.

### Leg 3 — the friction that used to enforce this is gone

See "The guardrail that disappeared" above. In a TypeScript codebase, adding LangGraph meant adding Python. It does not any more. So the rule becomes explicit:

> **An agent framework is a runtime-privileged dependency and needs a ledger line in [../coderules/dependencies.md](../coderules/dependencies.md) naming what it does that your own code cannot.** "Everyone uses it" is not that.

### What would change the answer

Falsifiable rather than dogmatic. Two things, and neither has happened:

1. **The pipeline gains genuine autonomy** — the model deciding which phase runs next, or how many times.
2. **Multi-agent generation becomes real** — a critic model iterating against a builder model across whole experiences.

**Bounded loops do not count, and this matters because one is already specified.** v2's visual verification loop ([pipeline-tools.md](pipeline-tools.md)) renders a scene, shows it to a vision critic, and applies **at most one** revision. That is a `for` loop with a limit of 1, written in the seam, roughly forty lines. A `while` with a max of 2 is a `while` with a max of 2 — the model is not choosing how many times it runs, your code is.

If one of the two triggers does fire, the Python-native answers are **Pydantic AI** (closest to a Pydantic-first stack, and the smallest of them) or **LangGraph** (the most control, and the CVE surface above). Take the tax deliberately; do not drift into it.

### What is worth considering, and is not a framework

The seam needs *something* to make the HTTP call. Three honest options, now Python:

| | |
|---|---|
| **Plain `httpx`** | OpenRouter is OpenAI-API-compatible. The seam is a function, a Pydantic model, and a `model_validate`. Zero framework, total clarity, and it is what ponytail says to do first |
| **The OpenAI SDK, pointed at OpenRouter** | Retries, streaming, and timeouts you would otherwise write. Small, boring, well-understood — and it is a client, not an orchestrator |
| **Instructor** | Takes a Pydantic model, validates the response, and retries with the validation errors as context. ~3M monthly downloads. This is the Python analogue of what `generateObject` used to be in the TypeScript plan, and it is *exactly* this pipeline's shape |

**Start with plain `httpx`.** Move to Instructor if the seam starts growing retry, streaming, and schema-marshalling code of its own — at that point it is deleting your code rather than adding to it, which is the only good reason to take a dependency ([../coderules/dependencies.md](../coderules/dependencies.md)).

One caution if you take it: Instructor's automatic retry would sit on top of the seam's **single** repair retry, and two retry layers multiply into a denial-of-wallet surface. Configure it to one attempt, or let it own the repair entirely — never both.

> **Note on the word "harness."** In this repo "harness" always means the **eval** harness ([Evals](#evals--the-missing-apparatus)) — Promptfoo and the golden briefs. Since 2026 the word also names agent *runtimes* (Microsoft's Agent Framework Harness reached GA in August 2026; the OpenAI Agents SDK ships a "model-native harness"). This project has the first and deliberately does not have the second.

## What to instrument from the first call

Because none of the above is decidable without data, and because it is far cheaper to log from day one than to retrofit:

- **Model id and provider route** on every call — under OpenRouter, "which model" and "which provider served it" are different questions and both matter
- **Repair rate**, per phase and per model. The number that decides everything
- **Tokens and calls**, both, given the pricing divergence above
- **Latency**, split into time-to-first-scene and total — perceived speed is what users judge ([../coderules/performance.md](../coderules/performance.md))
- **Refusals and error classes**, distinct from validation failures

All of it metadata. **No prompts, no outputs** — [../security/tenancy-and-data.md](../security/tenancy-and-data.md), unchanged.
