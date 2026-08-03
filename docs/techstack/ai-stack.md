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

- **Vision is no longer scarce.** ~67 models have vision, and **28 of those are open-weight and self-hostable**. Art-direction derivation ([../v3/ai-art-direction.md](../v3/ai-art-direction.md)) is not gated on a single vendor.
- **Pricing models are diverging.** Some providers are moving from token meters to task quotas (Kimi Code bills 300–1,200 calls per 5-hour window). Cost accounting that assumes per-token billing will eventually mismeasure. Log both calls and tokens.

## What actually constrains the choice here

Benchmarks are close to useless for this product because none of them measure the thing it needs. Four criteria do, in order:

**1. Schema conformance rate.** The Build phase emits a `Scene` tree that must satisfy Zod. The metric is the **repair rate**, and it is the single number that determines whether a model is usable here. A model that scores brilliantly on reasoning and emits a malformed union discriminator 8% of the time is worse for this job than a cheaper model that never does.

Under OpenRouter this matters more than it would with decoder-enforced structured outputs, because enforcement varies by provider ([decisions.md](decisions.md)). Measure it per model *and per route*.

**2. Design judgment under constraint.** Build does not write CSS — it chooses layout, emphasis, motion intent, and copy that fits a character budget. That is a taste-and-constraint task, and it correlates poorly with coding or math benchmarks. **The only way to know is to look at rendered output.**

**3. Vision quality, for v3 only.** AD derivation and the visual verification loop ([pipeline-tools.md](pipeline-tools.md)) need a model that reads type character, density, and spatial rhythm from an image. Distinct capability, distinct evaluation, possibly a distinct model.

**4. Cost, last.** At roughly $0.20 per experience ([../v1/ai-pipeline.md](../v1/ai-pipeline.md)), token cost is not this product's constraint and never has been. Cost matters for the *cheap* phases — Director, Intake, Edit run often and are structurally simple — and it is close to irrelevant for Build, where quality is everything.

> The one-line rule: **spend on Build, economise everywhere else, and let evals decide where the line falls.**

## Evals — the missing apparatus

This is the real gap the model question exposes. Model-neutrality without evals is not a strategy.

**v1 already specifies the dataset and does not call it one.** [../v1/spec.md](../v1/spec.md)'s verification step — *"5 golden briefs → run Director + Build → assert 100% Zod-valid output"* — is a golden dataset. Growing it into a proper eval set is the highest-leverage AI work in the project after the renderer itself.

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

**Langfuse** for tracing, prompt versioning, and building datasets *from production traces* — self-hostable, so prompts and outputs never leave your infrastructure. That last property is not a preference: [../security/tenancy-and-data.md](../security/tenancy-and-data.md) forbids storing prompts or outputs, because a prompt here is a customer's unreleased launch messaging under embargo. **A hosted eval platform that ingests full traces is in direct conflict with that rule.**

Self-hosted Langfuse resolves it, and only if traces are scrubbed and retained deliberately. **Do not adopt a trace-ingesting tool without deciding what it stores first** — this is the same failure as the Sentry configuration in [backend.md](backend.md), with a larger blast radius because tracing captures prompts by design rather than by accident.

**Prompts are versioned artifacts.** A prompt change is a behavior change with no type system behind it — it should be reviewable in a diff, tied to eval results, and rollback-able. In the repo, not in a database, so it moves through the same gate as the code.

## Language: TypeScript, with one named exception

Everything stays TypeScript — app, both workers, the pipeline. The reasons are specific rather than aesthetic:

- **The pipeline is not ML work.** It is HTTP calls returning JSON validated by Zod. Python's advantage is numerical and training ecosystems, none of which appear here.
- **The `Scene` schema is the source of truth**, and it is Zod ([../coderules/typescript.md](../coderules/typescript.md)). A Python service would need Pydantic models mirroring it — a second definition of the most important shape in the system, which is precisely the drift the one-source rule forbids.
- **One language is one toolchain**, one CI, one deployment story, one set of rules. For a solo build, a second language is a permanent tax.

The TypeScript AI ecosystem is now sufficient for this shape of work: the Vercel AI SDK is at ~11.5M weekly downloads, and Mastra reached 1.0 in January 2026 with 300K+ weekly downloads.

**The one thing genuinely better in Python is programmatic prompt optimization** — DSPy compiles prompts against an eval set instead of you hand-tuning them, and it has no real TypeScript equivalent.

> **Trigger for adding a Python service:** you have a golden dataset of 50+ briefs with quality scores, and you are spending real time hand-tuning the Build prompt against it. At that point DSPy is a small, isolated, offline service that *outputs a prompt* — not a runtime dependency. Anything short of that is a second language for a problem you do not have.

## Agent framework: none

LangGraph, CrewAI, Mastra, the OpenAI Agents SDK, Pydantic AI, Microsoft Agent Framework — all mature, several genuinely good, and **none of them belong here.**

**Because this pipeline is not an agent.** The four phases are a fixed sequence decided by your code, with a human gate in the middle:

```
Intake ──▶ Director ──▶ [human approves outline] ──▶ Build ──▶ Edit
```

No autonomous planning, no dynamic tool selection, no multi-agent negotiation, no memory across runs, no self-directed loops. An agent framework's entire value is orchestrating decisions the model makes about *what to do next* — and here your code makes every one of them. Adopting one would mean expressing four sequential function calls as a graph, adding a dependency, a state model, and a debugging surface, and buying nothing.

This is also why most of the OWASP Agentic Top 10 does not apply ([../security/adversarial-ai.md](../security/adversarial-ai.md)). **The absence of a framework is the same fact as the absence of the risk class.**

Two things that would change the answer, so the decision is falsifiable rather than dogmatic:

1. **The pipeline gains genuine autonomy** — the model deciding which phase runs next, or how many times. Bounded loops do not count; a `while` with a max of 2 is a `while` with a max of 2.
2. **Multi-agent generation becomes real** — a critic model iterating against a builder model across whole experiences.

If either happens, **Mastra** or the **Vercel AI SDK** are the TypeScript-native answers, and Mastra routes through the AI SDK anyway.

### What is worth considering, and is not a framework

The seam needs *something* to make the HTTP call. Three honest options:

| | |
|---|---|
| **Plain `fetch`** | OpenRouter is OpenAI-API-compatible. The seam is a function, a schema, and a parse. Zero dependencies, total clarity, and it is what ponytail says to do first |
| **An OpenAI-compatible client** | Retries, streaming, and timeouts you would otherwise write. Small, boring, well-understood |
| **Vercel AI SDK** | `generateObject` takes a Zod schema directly and returns a typed, parsed object — which is *exactly* this pipeline's shape, plus provider switching and streaming helpers |

Start with plain `fetch`. Move to `generateObject` if the seam starts growing retry, streaming, and schema-marshalling code of its own — at that point the SDK is deleting your code rather than adding to it, which is the only good reason to take a dependency ([../coderules/dependencies.md](../coderules/dependencies.md)).

## What to instrument from the first call

Because none of the above is decidable without data, and because it is far cheaper to log from day one than to retrofit:

- **Model id and provider route** on every call — under OpenRouter, "which model" and "which provider served it" are different questions and both matter
- **Repair rate**, per phase and per model. The number that decides everything
- **Tokens and calls**, both, given the pricing divergence above
- **Latency**, split into time-to-first-scene and total — perceived speed is what users judge ([../coderules/performance.md](../coderules/performance.md))
- **Refusals and error classes**, distinct from validation failures

All of it metadata. **No prompts, no outputs** — [../security/tenancy-and-data.md](../security/tenancy-and-data.md), unchanged.
