# Phase 06 — Model seam and the Build phase

> One call site for every model request in the codebase, and the phase that turns an approved outline into scenes. The seam owns validation, repair, refusal handling, metering, and caps — because a second call path is a second place for each of those to be missing.

**Depends on:** [04](04-renderer.md) — **hard gate, see below** — and [01](01-scene-schema.md) · **Blocks:** [07](07-director.md), [08](08-intake.md), [09](09-editor.md) · **Spec step:** 5

> **Entry gate:** phase 04 looks genuinely good. If it does not, building the thing that fills it is building a pipeline that produces disappointing pages faster. [../spec.md](../spec.md), Risk 1.

---

## Search

**Read first**

- [../ai-pipeline.md](../ai-pipeline.md) → "Phase 3 — Build", in full. The seam's four responsibilities, the prompt contract, the caching mechanics, the parallel-build trap
- [../../coderules/patterns.md](../../coderules/patterns.md) → rule 6, the seam; rule 5, failing closed
- [../../techstack/ai-stack.md](../../techstack/ai-stack.md) → "What to instrument from the first call"
- [../../techstack/pipeline-tools.md](../../techstack/pipeline-tools.md) → the three tiers. v1 ships tier 0 only
- [../../security/prompt-injection.md](../../security/prompt-injection.md) → Defenses 2 and 5
- [../../techstack/backend.md](../../techstack/backend.md) → "Model access: OpenRouter behind a seam", and what the trade costs

**Grep for**

- `api/schema/__init__.py` — `SCENE_JSON_SCHEMA`, `assert_no_presentational_values`, `assert_assets_resolve`. All three already exist. The seam calls them; it does not reimplement them
- `api/lib/result.py` — every model call returns `Result`. A refusal is a `Result` failure, not a raise and not a silent empty string
- `api/db/tenant.py` — `generations` writes go through `as_user` like everything else
- **Before writing a retry:** there is one repair retry and it lives in the seam. Not per phase, not per call site

**Verify externally**

- OpenRouter's current structured-output parameter name and its per-provider enforcement notes. `strict: true` is honoured natively by some providers, translated by others, and treated as a hint by the rest — the seam must never assume it held
- Per-route prompt-caching behaviour: whether activation is automatic or requires explicit breakpoints, the read discount, the write premium, and the minimum cacheable prefix. These vary by roughly 5× on the discount alone and getting it wrong silently costs 10× on the largest phase
- Whether the route bills tokens or task quotas. Some providers now bill call windows, and cost accounting that assumes per-token will mismeasure

---

## Make

### 1. The seam — `api/ai/complete.py`

```python
async def complete[T](
    phase: Literal["intake", "director", "build", "edit"],
    schema: type[T],              # a Pydantic model
    system: str,                  # the stable, cacheable prefix
    user: str,                    # the only part that varies
    tools: list[Tool] | None = None,   # tier 0 only
) -> Result[T]: ...
```

Plain `httpx` against an OpenAI-compatible endpoint. **Not Instructor, not an agent framework.** The pipeline is four sequential calls your code decides between, with a human gate in the middle — that is not an agent, and a framework would express four function calls as a graph, add a state model and a debugging surface, and buy nothing ([../../techstack/ai-stack.md](../../techstack/ai-stack.md)).

**Two reasons to hold that line here specifically**, because this is the phase where it is most tempting to cross:

- **It would be privileged.** `api` holds the database credentials, the model key, and later the integration tokens. The agentic-framework CVE class is under active exploitation ([../../security/platform-and-packages.md](../../security/platform-and-packages.md)) and this is the process it would land in.
- **The friction is gone.** In a TypeScript codebase, adding LangGraph meant adding a language. Now it is one line in `pyproject.toml` — which is why phase 00 put a CI grep on exactly those package names.

Take **Instructor** later only if the seam starts growing retry, streaming, and schema-marshalling code of its own, at which point it deletes your code rather than adding to it. If you do: **cap its retry at one**, or it multiplies with the repair below into a denial-of-wallet surface.

The seam owns six things, and each is a rule from elsewhere that a second call path would drop:

| | |
|---|---|
| **Pydantic parse of the response** | The real gate. The decoder only shifts the odds |
| **One repair retry** | The scene, the specific errors, and nothing else. Still invalid → surface honestly. Never retry forever, never silently drop |
| **Refusal normalization** | A declined request arrives as a **successful** HTTP response with empty or partial content, and the field that says so differs by provider. `if refusal := detect_refusal(raw): return err(Refused(...))`. Code that reads the first content block unconditionally crashes on the first refusal |
| **The metadata log** | Model id **and** provider route — different questions under a router. Tokens **and** calls. Repair flag, error class, latency split into time-to-first-scene and total |
| **Tool-call caps** | Total calls per generation, hard. Denial of wallet, same class as unbounded repair |
| **Quota and kill switch** | Checked **before** the call, atomically, failing closed |

### 2. Quota and kill switch — pulled forward

A sixth table, and [../spec.md](../spec.md) says five. The justification is explicit: an unattended repair loop against your own key is the one way v1 costs real money, and the check must be transactional anyway to close the A10 race.

```sql
update quotas set used = used + 1
where account_id = $1 and used < "limit"
returning used;
```

**Atomic increment, not read-then-write.** No row returned means refused. The check and the consumption are the same operation, so there is no window between them ([../../techstack/backend.md](../../techstack/backend.md)).

The kill switch is a single flag read before every call. Unreadable → **halted**, not permitted. Anything that grants, fails closed ([../../coderules/patterns.md](../../coderules/patterns.md), rule 5).

### 3. `generations` — and what never goes in it

```
generations  id, experience_id, phase, model_id, provider_route,
             tokens_in, tokens_out, calls, cached_tokens,
             repaired (bool), error_class, duration_ms, created_at
```

**No prompts. No outputs. No brief content.** A brief here is a customer's unreleased launch messaging under embargo ([../../security/tenancy-and-data.md](../../security/tenancy-and-data.md)). Phase, counts, a repair flag, an error class, and a duration answer both questions this table exists for — what an experience costs, and which validation rules fail most — without storing any of it.

`cached_tokens` is in the list because it is how you find out caching silently never activated. Zero across a whole build means either an invalidator in the prefix or a route where caching was never on, and the two look identical on the invoice.

### 4. The Build phase — `api/features/generation/`

```
api/features/generation/
  __init__.py
  build.py                one call per scene, streamed
  prompts/build.py        prompts are code, in the repo, reviewed in the diff
  tools.py                get_brand_kit · list_assets · get_constraints
  checks.py               post-build: no-styling, href provenance, claim provenance
  generation_data.py      generations, quotas
  test_generation.py
```

**One call per scene**, each receiving the full outline as context so scenes know their neighbours, each returning exactly one `Scene`. Streaming per scene is a perceived-speed decision: the user watches the experience assemble and can abort a bad direction on scene 2 rather than paying for 12.

**The prompt contract**, in order of importance ([../ai-pipeline.md](../ai-pipeline.md)):

1. Output valid `Scene` JSON, nothing else
2. Use only copy derived from `keyMessages` and `proofPoints` — invent nothing
3. Never emit colours, sizes, fonts, durations, or easing
4. Respect character limits; they are hard, stated as numbers
5. Prefer fewer blocks. Two usually beats six

Point 3 is enforced **by omission first and by rejection always** — the schema has no field where a hex code fits, so the model is not being asked to resist a temptation the vocabulary never offered. Point 4 is the one that needs stating as a hard number, because prompting is the only portable lever on output length and `maxLength` does not survive into structured-output enforcement.

**Caching discipline**, which is portable even where the mechanism is not:

- Never interpolate a timestamp, UUID, or scene index into the system prompt. They sit at the front and invalidate everything after them
- Serialize the schema deterministically — phase 01 already built that
- Put the scene-specific instruction **last**, after everything shared
- **Send scene 1, await its first streamed token, then fire the remaining scenes.** A cache entry only becomes readable once the first response begins streaming; twelve concurrent requests with the same prefix all pay full price. This costs one round trip and matches the streaming UX anyway

### 5. Tools — tier 0 only

`get_brand_kit()` · `list_assets()` · `get_constraints(ad)`. Pure reads of the user's own approved data. No state, no network, no consequence.

**Tool arguments are external input.** One Pydantic parse at the tool boundary, and ownership checked there — and because ownership is an authorization decision, it **fails closed**. An injected "read document 7" must die on ownership, not on the model politely declining ([../../coderules/python.md](../../coderules/python.md)).

`list_assets` is how the Build phase selects imagery: **by id, from what the user actually uploaded.** Same "arrange, never invent" rule as `CTA.href`. An `assetId` resolving to nothing is a validation failure, not a broken image on someone's launch page.

The line that does not move: **no tool with side effects.** If a future feature wants one, [../../security/prompt-injection.md](../../security/prompt-injection.md) needs rereading in full.

### 6. Post-build checks — the layer that actually catches things

Three, all in `checks.py`, all running on every generated tree before it is stored:

| Check | |
|---|---|
| **No presentational values** | `assert_no_presentational_values`. This is the control that catches what the decoder was previously assumed to prevent, and it matters *more* now, not less |
| **`CTA.href` provenance** | Every href traces to a URL the Brief supplied, plus a scheme allowlist. Makes an injected phishing link structurally impossible rather than filtered |
| **Claim provenance** | Any `Stat.value` not traceable to a `proofPoint` is flagged. [../ai-pipeline.md](../ai-pipeline.md) says this is the only one of the three claim-rule layers that actually catches things. Build it |

### 7. Streaming to the client

SSE from FastAPI — an async generator out, `EventSource` in. No dependency on either side. The unit is a **whole validated scene**, not a token, so partial-object streaming and mid-stream JSON repair solve problems this pipeline does not have. Anything that failed validation never reaches the client at all.

**The stream crosses the language boundary, which is the one new thing here.** `web` holds the `EventSource`; `api` produces the events. Keep the event payloads plain JSON matching the generated schema — no framing that only one side understands, or the boundary becomes a place where two representations of a scene exist.

```
event: scene   data: { "index": 2, "scene": { … } }
event: repair  data: { "index": 3 }
event: done    data: { "count": 8 }
```

**Keep the event logs of runs whose output you liked.** Serialize the stream to `evals/recordings/`, versioned next to the golden briefs below. Replayed client-side it drives the same renderer and is indistinguishable from a live generation, which is what the marketing site's demo is built from ([../../design/website.md](../../design/website.md)) — and it costs bytes now versus a model call and an unreproducible result later. It is a fixture, not code: nothing imports it, and it is also the fastest way to develop the client below without spending a call per reload.

### 7b. What the client does with those events

The generation watch is roughly forty seconds long, it is what someone describes to a colleague afterwards, and it is the highest-leverage motion design in the product ([../../design/app.md](../../design/app.md)). Since whole validated scenes arrive, there is nothing partial to hide behind a progress bar — **render the real scenes, full size, in place, in the artifact's own motion vocabulary.** The reveal the user watches is the reveal their audience gets.

| | |
|---|---|
| **The outline is visible ahead, ghosted** | Watching known slots fill beats watching an unknown list grow. Phase [07](07-director.md) already produced the outline this needs |
| **`repair` is silent** | It is instrumentation. Showing a user a self-correction is honesty nobody asked for, spent in the one moment the product cannot afford it |
| **Abort is prominent** | Killing a bad direction early is the stated reason streaming exists at all ([../../coderules/performance.md](../../coderules/performance.md), hot path 2) |
| **Failure at scene 6 of 8 keeps the five** | Never discard completed work. Offer to continue |
| **No invented steps** | "Writing headline…" progress theatre is the most common slop pattern in AI UI, and the events are real phase labels already |
| **Reduced motion respected here too** | The hardest place to get it right, and the place it is most often skipped |

### 8. The five golden briefs

Write them now, in `evals/briefs/`. They are the phase's test fixture and **the seed of the eval set that decides model selection from v2 onward** — growing them into a real dataset is the highest-leverage AI work in the project after the renderer.

Promptfoo, structural assertions only, running in CI as a hard gate. Quality scoring is a v2 concern and must never gate a merge — a probabilistic judge that blocks a deploy is how a gate becomes decoration.

---

## Verify

**The gate** — green.

**Pipeline** ([../spec.md](../spec.md) → Verification, row 4 — *"the one automated check that matters"*)

- [ ] 5 golden briefs → Build → **100% schema-valid after at most one repair**
- [ ] Every generated tree passes all three post-build checks
- [ ] A deliberately malformed model response triggers exactly one repair, and a second failure surfaces honestly rather than dropping the scene
- [ ] A simulated refusal becomes a `Result` failure the caller cannot ignore — not an empty scene

**Instrumentation** ([../../techstack/ai-stack.md](../../techstack/ai-stack.md))

- [ ] `generations` records model id **and** provider route, tokens **and** calls
- [ ] `cached_tokens` is non-zero from scene 2 onward. Zero across a whole build means the prefix has an invalidator or the route never had caching — investigate before accepting the cost figures
- [ ] Repair rate is queryable per phase and per model from day one. It is the number that decides everything later

**Security — the rows that go live here** ([../../security/testing.md](../../security/testing.md))

- [ ] **Injection corpus** against the only untrusted path v1 has — user-pasted text. Direct override · role confusion · exfiltration · href hijack · Slot poisoning · encoding tricks · claim tampering · tool abuse. Assertions: output is valid `Scene` JSON · no `Slot` contains a network call · every `CTA.href` traces to the Brief · no system-prompt fragment appears in any output field
- [ ] Injection is probabilistic, so **track a rate, not a pass/fail** — but assertions 1–3 are structural and absolute
- [ ] **Failing closed:** quota service throws → generation refused, **no model call made**. Kill switch on → all generation halts. Rate limiter unreachable → treated as tripped
- [ ] **The race:** N parallel requests against a balance of 1 → exactly one succeeds. This does not show up in a sequential test
- [ ] Tool-call flooding → capped, generation halted
- [ ] `read_*` with an id the user does not own → rejected on ownership, fails closed
- [ ] **`generations`, app logs, and error reports contain no prompt, scene, or brief content.** Grep the table and the log output with a canary string in the brief

**Cost**

- [ ] An 8-scene build lands within an order of magnitude of the ~$0.20 worked example. If it does not, caching is the first suspect

---

## Skipped

| Not built | Trigger |
|---|---|
| The visual verification loop | v2, and it cannot precede the thing it inspects. It roughly doubles cost to ~$0.40, which is a quality decision with a rounding error attached ([../../techstack/pipeline-tools.md](../../techstack/pipeline-tools.md)) |
| `render_preview` as a tool | Same — it is the loop's mechanism |
| Per-phase model selection | Decided by measured repair rate against real briefs, not by a name in a document. The instrumentation above is what makes the decision possible |
| Quality scoring evals | v2, nightly, tracked as a trend, never gating |
| Langfuse tracing | v3, self-hosted only. Do not adopt a trace-ingesting tool before deciding what it stores — tracing captures prompts by design ([../../techstack/ai-stack.md](../../techstack/ai-stack.md)) |
| DSPy / GEPA prompt optimization | 50+ scored briefs with quality scores exist and you are hand-tuning the Build prompt against them. It is native now rather than a second language — which is exactly why the constraint has to be explicit: **offline only, and its output is a prompt artifact committed to the repo**, never a runtime import ([../../techstack/ai-stack.md](../../techstack/ai-stack.md)) |
| Instructor | The seam grows its own retry, streaming, and schema-marshalling code. Then it deletes code rather than adding it — and its retry gets capped at one |
| An agent framework | Genuine autonomy (the model choosing which phase runs next) or real multi-agent generation. A bounded loop is not either ([../../techstack/ai-stack.md](../../techstack/ai-stack.md)) |
| Parallel builds beyond the cache-warming pattern | Layout repetition is prevented upstream by the director assigning layouts. Mark it `ponytail:` if it ships without that |

---

## Exit gate

- [ ] Exactly one model call site exists in the system, and the lint/grep proves it. `web` holds no model credential, so this is architectural as well as enforced
- [ ] No agent framework is in `pyproject.toml`, asserted by CI
- [ ] 5 golden briefs, 100% valid after ≤ 1 repair, in CI as a hard gate
- [ ] All three post-build checks run on every tree
- [ ] Quota is atomic, the kill switch halts, and both fail closed under injected failure
- [ ] Injection corpus runs and its rate is recorded
- [ ] `generations` holds metadata and nothing else — proven with a canary
- [ ] Caching is verified active, not assumed
