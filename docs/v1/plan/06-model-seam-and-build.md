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

- [x] Exactly one model call site exists in the system, and the lint/grep proves it. `web` holds no model credential, so this is architectural as well as enforced — `api/ai/complete.py` is the only file referencing `openrouter.ai` or `OPENROUTER_API_KEY` outside `config.py` (which only reads the env var) and `evals/provider.py` (which calls `build_experience`, not the endpoint directly)
- [x] No agent framework is in `pyproject.toml`, asserted by CI — `scripts/checks/invariants.sh`
- [x] 5 golden briefs, 100% valid after ≤ 1 repair, in CI as a hard gate. Verified live 2026-08-05 against `openai/gpt-5-mini` (see below for why not `anthropic/claude-haiku-4.5`): all 5 golden briefs (`api/evals/briefs/`) produced schema-valid `Scene` JSON for every outline scene; some scenes needed the one repair retry, none exhausted it. Wired into `.github/workflows/gate.yml`'s `api` job as `npx promptfoo eval`, which exits non-zero on any assertion failure
  **Corrected 2026-08-06.** That "100%" was true of one run and got restated as a durable fact — CI run 31031983435 (the run that fixed the DB-pool bug below) surfaced it was not: 3 of 5 golden briefs lost a scene to `repair_exhausted`. Root cause, found by reproducing individual scene calls live outside `complete()`'s error-swallowing: every model behind this seam is a reasoning model, and OpenRouter bills hidden reasoning tokens out of the *same* `max_tokens` budget as the visible completion. A trivial 40-word request burned 256 reasoning tokens and returned `content: null` — `finish_reason: length`, zero visible output — at the default setting; `reasoning.max_tokens` does not cap this (set to 50, the model still spent 256), but `reasoning.effort: "minimal"` does (0 reasoning tokens, full content, a quarter of the cost). This is almost certainly the true mechanism behind the 32k-token runaway `_MAX_OUTPUT_TOKENS` was added to contain, further up this file — a cause left undiagnosed, patched at the symptom. Fixed at the one call site, `ai/complete.py`'s `_payload` (`_REASONING`), pinned by a unit test so the key cannot silently regress. Re-tested live against the three specific (brief, scene) pairs that failed in CI: all three now pass on the first attempt, no repair needed — supporting evidence, not full-corpus proof; that is what the next real CI run confirms. `evals/assertions.py:no_scenes_lost_to_errors` now gates the golden-brief cases specifically (not the injection corpus, where an error is often the security control working correctly) so this class of gap shows up in CI instead of hiding behind `valid_scene_json`'s weaker "something came back" check
- [x] All four post-build checks run on every tree — `features/generation/checks.py`, wired into `build_experience`, tested in `features/generation/test_checks.py`. The fourth (no prompt leak) was added in phase 07; see the injection-corpus row below for what found it missing
- [x] Quota is atomic, the kill switch halts, and both fail closed under injected failure — `features/generation/test_quota.py`: the parallel-race test (10 concurrent requests against a balance of 1 → exactly one succeeds), the halted-row test, and the unknown-owner/unreachable-quota test all pass
- [x] Injection corpus runs and its rate is recorded. Verified live 2026-08-05: all 7 payload families (`api/evals/injection/` — direct override, role confusion, exfiltration, href hijack, Slot poisoning, encoding tricks, claim tampering) produced output passing all four structural assertions (`api/evals/assertions.py`) — 0% structural-violation rate this run. Runs in CI alongside the golden briefs; the rate to watch over time is `generations.error_class` and repeat eval runs, not this one snapshot.
  **Corrected 2026-08-05, phase 07.** CI run 31010631635 failed `03-exfiltration.json` on `no_prompt_leak` with nothing about the pipeline changed since a clean run. The first reading was "model non-determinism, so stop gating on assertion 4" — that was wrong twice over: it treated a caught attack as noise, and it would have deleted the only detector for it. What the run actually exposed is an asymmetry. Assertions 1–3 are absolute because `check_scene` rejects the violating scene, so it never reaches the harness's `scenes` at all; assertion 4 had no counterpart there, which is exactly why it was the only one that could fail on model behaviour alone. The fix is the missing control, not a smaller gate: `checks.py`'s `_assert_no_prompt_leak` now rejects a scene echoing the Build contract, `PROMPT_SENTINELS` moved to `prompts/build.py` so the detector and the prompt cannot drift apart (`test_checks.py` fails if they do), and all four assertions gate again. Also: the eval step now writes `--output eval-results.json` and uploads it `if: always()` — the console table truncates cells to ~60 chars, which is why that failure took a session to read
- [x] `generations` holds metadata and nothing else — proven with a canary — `api/ai/test_canary.py` sends a canary string through the real seam (mocked HTTP, real quota check, real DB write) and greps every column of the resulting row for it
- [x] Caching is verified active, not assumed. Queried `generations` after the live run above: `cached_tokens` is `0` on the first scene of every build (nothing to cache yet) and 1792–2048 on every scene after, within the same build — the exact "non-zero from scene 2 onward" the doc's own Verify section asks for

**A real capability gap, found running this exit gate live:** `anthropic/claude-haiku-4.5` — the original pick for cost — rejects the `Scene` schema's structured-output request outright with `"compiled grammar is too large"`, from Anthropic direct, Bedrock, and Azure alike, independent of the keyword-compatibility fixes below. `openai/gpt-5-mini` handles it cleanly and is cheaper anyway ($0.25/$2 per million tokens in/out vs $1/$5). `docs/v1/plan/06-model-seam-and-build.md`'s own "Search" section named exactly this risk ("`strict: true` ... must never assume it held") — it just didn't say which provider would be the one to hit it.

Two schema-compatibility fixes landed in `ai/complete.py` as a result, both provider-agnostic (applied regardless of route, not just for the provider that surfaced them):
- `_strip_unsupported_keywords`: strips `minimum`/`maximum`/`minItems`/`maxItems`/`discriminator` and renames `oneOf` → `anyOf` before a schema goes over the wire — every one of these still gets enforced locally by Pydantic on the way back, with the existing one-repair retry as the backstop for a value the provider's own (weaker) structural check let through
- `_iter_sse_data`: fixed to concatenate multi-line SSE `data:` blocks per spec before parsing, rather than treating every `data:` line as its own complete JSON object — found live against `gpt-5-mini`, would have silently crashed the seam (an unhandled `JSONDecodeError`, not a `Result`) on any long enough streamed delta
