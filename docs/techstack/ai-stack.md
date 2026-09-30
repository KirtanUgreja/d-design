# AI Stack

Which models, chosen how, measured with what — and why there is no agent framework. **Rewritten 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)); the model seam itself is specified in [../v4/engine.md](../v4/engine.md) → "The model seam".

## The stance: no favourite model

**This product should not have a preferred model vendor.** It has a preferred *interface*: one module, `api/engine/llm/openrouter.py`, with a JSON call and a text call. Everything behind that is replaceable, and the choice of what sits there is an empirical question with a different answer per stage and a different answer every few months.

**The same stance applies to image generation**, which goes through the OpenRouter image-model route behind the same seam.

**The corollary is that opinions are worthless here and measurements are not.** A model is chosen for a stage because it scored better on the bench briefs, not because of a benchmark, a launch post, or a reputation. v4 is quality-first: the owner chose the best model over the cheapest on 2026-09-26, and the bake-off decides which one that is.

## Stages and models (v4)

| Stage | What the call does | Mode | Model role |
|---|---|---|---|
| **Interview** | ≤5 adaptive questions with suggested answers | JSON | Writing |
| **Research** | Searches the web and returns cited `Fact`s | JSON + `openrouter:web_search` | Writing, with search |
| **Storyline** | Governing thought, arc, a `SlidePlan` per slide, speaker notes | JSON | Writing. Top tier |
| **Theme and looks** | — | — | **No model.** A seeded sampler and pure code ([../v4/design-engine.md](../v4/design-engine.md)) |
| **Compose** | One slide's HTML and CSS, in parallel (5 at a time) | **Text** | Design. **Top tier — this is where the money goes** |
| **Repair** | The same slide again, with its measured defects | Text | Design. The bake-off decides whether a cheaper model is enough |
| **Images** | One image per slot the plan asked for | Image route | Image model, chosen by the phase-25 bake-off |

**Concrete ids are picked by the phase-22 bake-off**, two or three top models on the 3-brief smoke set, ranked by wall score, then dollars, then seconds. Candidates to **verify at phase start**, because every name here is stale on arrival: the current top Claude, GPT and Gemini models on OpenRouter. The measured starting point from v3 (2026-09-24): `anthropic/claude-sonnet-4.5` passed a cross-field layout task 4/4 where `openai/gpt-4o` passed 3/4 and `gpt-4o-mini` 0/3 ([../findings.md](../findings.md)).

**Model ids are pinned.** A stage's setting names an exact id, never an alias that a provider can repoint. A pin is what makes a bench score mean the same thing next week.

> The one-line rule is unchanged: **spend on the slide, economise everywhere else, and let the bench decide where the line falls.** v3 did the opposite. It ran `gpt-4o-mini` per slide to rewrite copy a stronger model had already written.

### Measured at phase 21 (2026-09-30)

Read from OpenRouter's model list and from live calls through `api/engine/llm/openrouter.py`.

| Candidate | Role | $ per M in / out | Cache read |
|---|---|---|---|
| `anthropic/claude-opus-5.5` | design | 4 / 20 | 0.20 |
| `anthropic/claude-sonnet-5.5` | writing | 2 / 10 | 0.20 |
| `anthropic/claude-haiku-4.5` | cheap (interview, smoke) | 1 / 5 | 0.10 |

These are the defaults in `api/settings.py` until the phase-22 bake-off pins the winners.

- **Cost comes back on the response.** With `usage: {include: true}` the reply's `usage.cost` is the dollar cost of the call; the ledger records it. A smoke call (177 tokens in, 9 out, Haiku) cost $0.00022.
- **Strict `json_schema` output works on the Claude models** through OpenRouter: 12 of 12 outline calls parsed first time.
- **One frozen outline costs about $0.01–0.025** on Sonnet 5.5.
- Not yet measured: whether `cache_control` registers cached tokens on these models, and the minimum cacheable prefix. Phase 22 measures both on the first compose run.

## The landscape

Stated so the seam has something concrete to be neutral about. Dated August 2026 and stale on arrival.

| Tier | Examples | Rough input/output per MTok |
|---|---|---|
| **Frontier** | Claude Mythos Preview · Claude Opus 5 · GPT-5 family · Gemini 3 Pro · Grok 4 · GLM-5 | ~$2.50–$10 / ~$15–$50 |
| **Mid** | Claude Sonnet 4.6 · GPT-5.4 · Kimi K3 | ~$2.50–$3 / ~$15 |
| **Budget** | DeepSeek V3.2 · Qwen3.7 Flash | cents |

Two structural notes that outlast the names:

- **Vision is no longer scarce**, and v4 does not lean on it. QA is measured, not judged by a vision model ([pipeline-tools.md](pipeline-tools.md)).
- **Pricing models are diverging.** Some providers bill task quotas rather than tokens. The cost ledger records calls, tokens and the dollar figure from the response's own usage accounting.

## What actually constrains the choice here

Benchmarks are close to useless for this product because none of them measure the thing it needs. Four criteria do, in order:

**1. Design judgment, seen on the wall.** Compose writes a slide's HTML and CSS inside a token system, with two or three exemplars in view. *(This replaces "Build does not write CSS", the v3 rule that capped output at about five visual variables.)* It is a taste-under-constraint task and correlates poorly with coding benchmarks. **The only way to know is to look at rendered output**, which is what the bench wall is for ([../v4/bench.md](../v4/bench.md)).

**2. First-pass QA rate.** The share of slides that pass lint and the measured checks without a repair. This is v4's version of the old repair rate: it decides latency and cost together, because every repair is another full compose call.

**3. Conformance on the JSON stages.** Interview, research and storyline return Pydantic-parsed JSON with one repair per call. Under OpenRouter, `strict` enforcement varies by provider ([decisions.md](decisions.md)), so measure it per model *and per route*.

**4. Cost, last, but capped.** The estimate is $1.5–3.5 per 10-slide deck, measured in phase 22. Every deck carries a **`budget_usd` hard cap that fails closed**: when the ledger reaches it the build stops and says so.

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

**In v4 this finding becomes a rule of the seam:** every stage sets its reasoning effort and `max_tokens` explicitly, and a `finish_reason` of `length` is a typed failure that is never parsed.

## Text mode for slide HTML

The seam has two calls, and the second exists for one reason.

| | |
|---|---|
| `complete_json(schema, …)` | A strict `json_schema` response format, then one Pydantic parse. On failure, **one repair per call**, carrying the real previous answer and the validation error |
| `complete_text(parse, …)` | For slide HTML. The model answers in tags (`<slide>…</slide><style>…</style>`) and our code parses them |

**HTML never travels as JSON.** Markup escaped inside a JSON string costs tokens on every quote and newline, and one missed escape breaks the whole response. A tagged text answer is cheaper and fails more gracefully. The safety of what comes back does not depend on the format either way: it is sanitized, linted and rendered without scripts ([../security/content-and-web.md](../security/content-and-web.md) → "AI-written HTML and CSS").

v3's seam was synchronous and counted repairs per request, which ruled out parallel slides and crashed on the case the repair existed for. The port fixes both.

## Web search

*(OpenRouter documentation, read 2026-09.)*

| | |
|---|---|
| **How** | `openrouter:web_search` in the request's `tools` array. It is a server tool: OpenRouter runs the search, and the model decides when to call it. The older `:online` suffix and `web` plugin still work and are deprecated |
| **Engines** | `exa` and `parallel` are the two v4 uses. `native`, `firecrawl` and `perplexity` also exist |
| **Cost** | Exa: ~$0.007 per request, which includes 10 results. Parallel: ~$0.001–$0.005 per request by mode. Search fees for a deck stay under $0.10; the rest is model tokens |
| **What comes back** | `url_citation` annotations: `url`, `title`, `content` (an extract of roughly 2,000–4,000 characters), and `start_index` / `end_index` into the answer |
| **What we do with it** | `research.py` turns each citation into a `Fact` with its URL, title and quote. A number without a `Fact` is flagged for the user ([../v4/content.md](../v4/content.md)) |

Two consequences belong to other documents: a search result is **untrusted input** ([../security/prompt-injection.md](../security/prompt-injection.md)), and a query built from a customer's brief **reaches a search engine** ([../security/third-parties.md](../security/third-parties.md)).

## Prompt caching

*(OpenRouter and Anthropic documentation, read 2026-09.)*

Compose is 8–10 calls per deck that share a long prefix: the slide rules, the theme, the exemplars. Caching that prefix is the largest cost lever in the pipeline.

| | |
|---|---|
| **Mechanism** | OpenRouter passes `cache_control` breakpoints through to Anthropic models. Other providers cache automatically or not at all, so check per model |
| **Price** | A cache read costs **0.1×** the input price. A write costs 1.25× (5-minute lifetime) or 2× (1-hour) |
| **Minimum prefix** | Varies by model: 1,024 tokens on the Sonnet 4.x line, 4,096 on recent Opus and Haiku 4.5. A prefix under the minimum is silently not cached |
| **Sticky routing** | A `session_id` per deck pins follow-up calls to the provider holding the warm cache |

**The rule that follows: stable content first.** Rules, then theme, then exemplars, then the one slide's plan last. Anything that varies per slide and sits early in the prompt throws the cache away. Phase 22 verifies the hit rate from `cached_tokens` in the usage accounting rather than assuming it.

## Evals

Model-neutrality without evals is not a strategy. v3 specified Promptfoo and Langfuse and wired up neither: its CI ran `pytest -q`, and its "variety gate" scored a stub model that wrote the variety itself.

v4's apparatus is the bench ([../v4/bench.md](../v4/bench.md)), in three layers:

| Layer | What it does | When it runs |
|---|---|---|
| **Structural assertions** | Lint passes · zero FAIL defects in QA · every number sourced or flagged · no banned phrase · the export makes zero requests · the hostile-slide and injection suites | Every commit that touches the engine. **Hard pass/fail**, on fixtures, no model call |
| **The wall** | Every slide of every bench deck on one page, scored 1–5 by the owner | Every phase exit. **The only judge of design** |
| **The ledger** | First-pass QA rate, repair rate, cost, latency per stage and per model | Every generation |

Layer 1 is deterministic and gates merges. Layer 2 is a human and gates phases. **No probabilistic judge gates anything**: a flaky judge blocking a merge is how teams learn to skip the gate, and AeSlides (arXiv 2604.22840) found vision-model reflection on slides counterproductive.

**Prompts are versioned artifacts.** They live in `api/engine/*/prompts/` as files, change in a diff, and carry a version that the cost ledger records per call.

**Promptfoo and Langfuse** return only if the bench outgrows plain Python. If a tracing tool is ever adopted, decide what it stores first: a prompt here is a customer's unreleased pitch ([../security/third-parties.md](../security/third-parties.md)).

## Language: Python for the backend, TypeScript for the UI

The backend is **Python (FastAPI)**. The decision was re-examined on 2026-09-26 and kept by the owner ([decisions.md](decisions.md) → "The Python backend, re-examined").

| | Language | Why it is there |
|---|---|---|
| **api** — routes, SSE | **Python** | The internet-facing process |
| **worker** — the engine, models, Chromium, export | **Python** | Same codebase, second entry point |
| **web** — the app | **TypeScript** | It is a React UI. It renders no slide |

**What changed in v4 is what crosses the boundary.** v3 generated the whole `Deck` tree from Pydantic into TypeScript types and a Zod validator, because a TypeScript renderer consumed it. In v4 slides cross as HTML, so the only thing generated is the API contract:

```
api/engine/models.py  (Pydantic — the one source)
   │
   └── FastAPI OpenAPI ──▶ openapi-typescript ──▶ web/lib/api/schema.d.ts   (no-diff gate)
```

Generated TypeScript is never hand-edited, and the gate fails if regenerating it produces a diff. SSE event models are not route responses, so they are registered in the OpenAPI schema explicitly.

### The guardrail that disappeared

This is the consequence most likely to bite, and it has nothing to do with schemas.

> **"It would be a second language" was doing real work.** It is what kept DSPy, LangGraph, CrewAI, and Pydantic AI out of this project without anyone having to argue against them. That barrier is gone. All of them are now one `pip install` away, in the process that holds the model key.

So every rule that was previously enforced by friction now has to be enforced on purpose. That is what the next two sections are.

### DSPy — now native, and still offline

The old claim that DSPy *"has no real TypeScript equivalent"* was already going stale: [`ax-llm/ax`](https://github.com/ax-llm/ax) is the de-facto TypeScript port and ships GEPA, the reflective Pareto optimizer. That correction is now moot — the pipeline is Python, so DSPy and GEPA are native.

**The trigger is unchanged and the shape of the answer is unchanged:**

> **When:** a golden dataset of 50+ briefs with quality scores exists, and you are spending real time hand-tuning the Build prompt against it.
>
> **What:** DSPy runs **offline** and its output is a **prompt artifact committed to the repo**, reviewed in a diff like every other prompt ([../coderules/tooling.md](../coderules/tooling.md)). It is never imported by the running API.

Being in the same language is not a reason to make it a runtime dependency. It is the reason that rule now has to be written down.

### DSPy — native, offline, and so far unused

DSPy/GEPA was the headline reason for the Python move. **As of 2026-09-26 nothing in `api/` imports it.** The trigger and the shape of the answer are unchanged:

> **When:** the bench has 50+ briefs with wall scores, and real time is going into hand-tuning the compose prompt against them.
>
> **What:** DSPy runs **offline** and its output is a **prompt artifact committed to the repo**, reviewed in a diff like every other prompt. It is never imported by the running backend.

## Agent framework: none

LangGraph, CrewAI, Pydantic AI, the OpenAI Agents SDK, Microsoft Agent Framework, Mastra — all mature, several genuinely good, and **none of them belong here.** The decision predates the Python move and survives it. It now rests on three legs instead of one.

### Leg 1 — this pipeline is not an agent

The pipeline is a fixed sequence decided by your code, with two human gates in it:

```
interview ──▶ research ──▶ storyline ──▶ [human approves outline] ──▶ looks ──▶ [human picks one]
   ──▶ compose (per slide) ──▶ QA + repair (≤2) ──▶ export
```

No autonomous planning, no dynamic tool selection, no multi-agent negotiation, no memory across runs, no self-directed loops. An agent framework's entire value is orchestrating decisions the model makes about *what to do next* — and here your code makes every one of them. **Web search does not change this.** `openrouter:web_search` is a read-only server tool: the model decides *what to search for* inside one research call, and nothing it finds can trigger an action. Adopting a framework would mean expressing a handful of sequential function calls as a graph, adding a dependency, a state model, and a debugging surface, and buying nothing.

This is also why most of the OWASP Agentic Top 10 does not apply ([../security/adversarial-ai.md](../security/adversarial-ai.md)). **The absence of a framework is the same fact as the absence of the risk class.**

### Leg 2 — it would be a runtime-privileged dependency, and this class is being exploited

*(researched August 2026)*

[../coderules/dependencies.md](../coderules/dependencies.md) already has the rule that decides this: **where a dependency runs is part of the decision.** A risky dependency belongs in a process with nothing worth stealing. An agent framework goes in the opposite place — the process that orchestrates, which in v4 is the **worker**, holding the model key and the deck store.

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

The point is not that LangChain is uniquely bad; it is the most-used and therefore the most-audited, which is why its CVEs are the ones with names. **The point is that adopting any of them puts a large, fast-moving, actively-targeted dependency in the one process that has something worth stealing** — to orchestrate function calls that are already in the right order.

### Leg 3 — the friction that used to enforce this is gone

See "The guardrail that disappeared" above. In a TypeScript codebase, adding LangGraph meant adding Python. It does not any more. So the rule becomes explicit:

> **An agent framework is a runtime-privileged dependency and needs a ledger line in [../coderules/dependencies.md](../coderules/dependencies.md) naming what it does that your own code cannot.** "Everyone uses it" is not that.

### What would change the answer

Falsifiable rather than dogmatic. Two things, and neither has happened:

1. **The pipeline gains genuine autonomy** — the model deciding which phase runs next, or how many times.
2. **Multi-agent generation becomes real** — a critic model iterating against a builder model across whole experiences.

**Bounded loops do not count, and this matters because one is specified.** The QA loop ([pipeline-tools.md](pipeline-tools.md)) renders a slide, measures it, and asks for **at most two** repairs. That is a `for` loop with a literal limit. The model is not choosing how many times it runs, your code is.

If one of the two triggers does fire, the Python-native answers are **Pydantic AI** (closest to a Pydantic-first stack, and the smallest of them) or **LangGraph** (the most control, and the CVE surface above). Take the tax deliberately; do not drift into it.

### What is worth considering, and is not a framework

The seam needs *something* to make the HTTP call. Three honest options, now Python:

| | |
|---|---|
| **Plain `httpx`** | OpenRouter is OpenAI-API-compatible. The seam is a function, a Pydantic model, and a `model_validate`. Zero framework, total clarity, and it is what ponytail says to do first |
| **The OpenAI SDK, pointed at OpenRouter** | Retries, streaming, and timeouts you would otherwise write. Small, boring, well-understood — and it is a client, not an orchestrator |
| **Instructor** | Takes a Pydantic model, validates the response, and retries with the validation errors as context. ~3M monthly downloads. This is the Python analogue of what `generateObject` used to be in the TypeScript plan, and it is *exactly* this pipeline's shape |

**Start with plain `httpx`.** Move to Instructor if the seam starts growing retry, streaming, and schema-marshalling code of its own — at that point it is deleting your code rather than adding to it, which is the only good reason to take a dependency ([../coderules/dependencies.md](../coderules/dependencies.md)).

One caution if you take it: Instructor's automatic retry would sit on top of the seam's **one repair per call**, and two retry layers multiply into a denial-of-wallet surface. Configure it to one attempt, or let it own the repair entirely — never both.

> **Note on the word "harness."** In this repo "harness" always means the **eval** harness ([Evals](#evals)) — the bench and its briefs. Since 2026 the word also names agent *runtimes* (Microsoft's Agent Framework Harness reached GA in August 2026; the OpenAI Agents SDK ships a "model-native harness"). This project has the first and deliberately does not have the second.

## What to instrument from the first call

Every call appends one `CostLedger` entry ([../v4/engine.md](../v4/engine.md) → "Data model"):

- **Stage, pinned model id, provider route and prompt version**
- **Tokens in, cached and out, and the dollar figure** from the response's usage accounting
- **Milliseconds**, and for a build the time to the first slide
- **Repair**, yes or no, and for compose whether the slide passed QA first time
- **`finish_reason` and error class**, distinct from validation failures

All of it metadata. **No prompts, no outputs** — [../security/tenancy-and-data.md](../security/tenancy-and-data.md), unchanged.
