# AI Pipeline

Four calls, not one. Each phase has a typed input, a typed output, and a validation gate.

```
Intake ──▶ Brief ──▶ Director ──▶ Outline ──▶ [user approves] ──▶ Build ──▶ Scene tree
                                                                              │
                                                                      Edit ◀──┘
```

**Every call in this document goes through one provider seam, and this product has no preferred model vendor** ([../techstack/ai-stack.md](../techstack/ai-stack.md), [../techstack/backend.md](../techstack/backend.md)). That decision post-dates the first draft of this document and changes several mechanics below — most of all what the decoder guarantees and how caching behaves. Where a mechanic varies by route, it is marked as such rather than stated as a fact about "the model".

The phases themselves are unaffected. Four calls with a human gate is a pipeline decision, not a vendor one.

## Why four phases and not one

A single "prompt → finished experience" call is the most impressive demo and the worst product. It burns the most tokens on results users reject, gives no intervention point, and makes every subsequent edit a regeneration.

Splitting it means the expensive call only runs against a structure the user already approved, and edits cost roughly 1% of a build.

---

## Phase 1 — Intake

**In:** conversation, an uploaded document, or a URL. **Out:** `Brief`.

```python
class Brief(BaseModel):
    goal: str                       # what this experience must achieve
    audience: str
    key_messages: list[str]         # 3-5, APPROVED copy — see below
    proof_points: list[str]         # stats, quotes, customer names
    tone: str
    cta: Cta                        # label + href
    assets: list[AssetRef]
    constraints: str | None = None  # legal, brand, must-not-say
```

Three entry paths, one output shape:

- **Import** — PDF, deck, doc, or URL. Extract, then ask only about what's missing.
- **Prompt** — freeform description. Fill what's inferable, ask about the rest.
- **Q&A** — no material at all. The AI interviews the user.

Always ask, never assume: `goal`, `audience`, `cta`. These three determine narrative structure, and guessing them wastes the entire downstream pipeline.

### Reading the uploaded document

**The document is parsed before the model sees it, and not by the model.** An uploaded PDF or deck is the single most hostile input in v1 — PDF parsers are the richest source of parser CVEs in the dependency tree ([../security/platform-and-packages.md](../security/platform-and-packages.md)) — so extraction runs in the **fetch worker**: the container with no database, no VPC route, and nothing worth stealing ([../techstack/backend.md](../techstack/backend.md)).

```
upload ──▶ quarantine prefix ──▶ fetch worker: caps, magic bytes, unpdf/pdf.js
                                              │
                                     extracted text ──▶ Intake model call
```

Caps are enforced **before** parse, not after: page count, byte size, and decompression ratio. A parser that has already allocated is a parser you have already lost.

Two tools give the model paged access to the result rather than one wholesale dump ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)):

| Tool | |
|---|---|
| `list_documents()` | Ids, filenames, page counts |
| `read_document(id, pages)` | Paged text, each page inside its own delimited untrusted-data frame |

Paging is not a performance decision. The same content reaches the model either way, so the injection risk is identical — but the blast radius per unit is smaller and there is an audit trail of which pages of a poisoned document were actually read.

**The documented fallback:** a frontier model reading the PDF natively — text, layout, and charts in one pass, no parser dependency at all. Slower, costs tokens, available immediately, and it is the right move the day a PDF advisory lands with no patch ([../techstack/infrastructure.md](../techstack/infrastructure.md)). Native document input is a per-provider capability, so the seam has to expose it rather than assume it.

### The claims rule

`keyMessages` and `proofPoints` are **approved copy**. Downstream phases may shorten, split, and rearrange them. They may not invent new claims, new statistics, new customer names, or new capabilities.

This is the single most important constraint in the pipeline. A marketer cannot ship a page asserting something untrue about their product, and one such incident costs more trust than a hundred good generations earn.

Enforcement is three-layered:
1. Stated explicitly in the build prompt
2. Visible at the outline gate, where the user reviews structure before copy is committed
3. A post-build check flags any `Stat.value` not traceable to a `proofPoint`

Layer 3 is the only one that actually catches things. Build it.

### The URL rule

The same principle covers links, and it is also a security control. **Every `CTA.href` the build phase emits is selected from URLs the user supplied** — the Brief `cta`, plus any explicit links in the source material. The AI never composes a new URL.

A post-build check rejects any `href` not tracing to a Brief-supplied URL, and a scheme allowlist rejects `javascript:`, `data:`, `vbscript:`, and protocol-relative URLs regardless. This makes an injected phishing link structurally impossible rather than filtered — see [../security/prompt-injection.md](../security/prompt-injection.md).

---

## Phase 2 — Director

**In:** `Brief`. **Out:** `Outline`. Cheap, fast, one call.

```python
class Outline(BaseModel):
    title: str
    scenes: list[OutlineScene]      # intent, beat, layout_hint?
```

`beat` is one sentence describing what this scene does in the narrative — not its copy. The director decides *structure and pacing*, nothing else.

Rules: 3–12 scenes · exactly one `hook`, first · at least one `cta` · no repeated adjacent intents.

**This is the user gate.** The outline renders as an editable list: reorder, delete, retitle, change intent, add a scene. Cheap for the user to fix a wrong narrative here; expensive after 12 scenes are built.

---

## Phase 3 — Build

**In:** `Brief` + approved `Outline` + `BrandKit`. **Out:** `Scene[]`, streamed one scene per call.

One call per scene. Each call receives the full outline as context so scenes know their neighbors, and returns exactly one `Scene` conforming to [scene-schema.md](scene-schema.md).

Streaming per scene matters for perceived speed: the user watches the experience assemble instead of staring at a spinner, and can abort a bad direction on scene 2 rather than paying for 12.

### The request goes through the seam

There is exactly one call site for model access in the codebase ([../coderules/patterns.md](../coderules/patterns.md), rule 6). The Build phase does not know which model or which provider served it.

```python
scene = await complete(
    phase="build",
    schema=Scene,              # Pydantic — the same class that validates the response
    system=BUILD_SYSTEM_PROMPT,# stable prefix: prompt, schema, brief, brand kit, outline
    user=scene_request,        # the only part that varies per scene
)
```

The schema handed to the model is `Scene.model_json_schema()`, produced in the same process that makes the call — so the constraint and the validator are one object and cannot drift ([../coderules/python.md](../coderules/python.md)).

The seam's job is to normalize four things that differ across providers, because every one of them is load-bearing here:

| | Why the seam must own it |
|---|---|
| **Schema enforcement** | `strict: true` is honored natively by some providers, translated by others, and treated as a strong hint by the rest. Never assume it held — see the validation table below |
| **Caching** | Some providers cache automatically, some require explicit breakpoints. The prefix discipline is yours either way |
| **Refusals** | A declined request may arrive as a success response with empty or partial content. The seam normalizes it into an error the caller cannot ignore |
| **Sampling and effort parameters** | Names, defaults, and legal ranges vary, and some models reject parameters others require. Steer with prompting, which is portable |

**Model choice per phase is deliberately not fixed here.** It is an empirical question answered by the repair rate against real briefs, not by a name in a design document — [../techstack/ai-stack.md](../techstack/ai-stack.md). What this document specifies is the *shape* of the call, which survives any model.

Two things the seam must not hide, because both are load-bearing for the cost figures at the end of this document: **per-route caching behavior** and **cost per phase**. Log them per call, alongside the model id and the provider that actually served the request — under a router those are two different questions.

### What the Build phase may call

v1 ships **tier-0 tools only** — pure reads of the user's own approved data, with no state, no network, and no consequence ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)).

| Tool | |
|---|---|
| `get_brand_kit()` | Colors, logo, font ids |
| `list_assets()` | Uploaded images with dimensions and alt text |
| `get_constraints(ad)` | Character budgets, layout regions, valid block types |

`list_assets` closes a real gap: earlier drafts required the Build phase to select imagery and never said how. **The model picks an asset by id from what the user actually uploaded** — the same "arrange, never invent" rule that governs `CTA.href`, applied to media.

**Tool-call arguments are external input and get one schema parse at the tool boundary** ([../coderules/README.md](../coderules/README.md), rule 2). `read_document(id)` where `id` is not one of *this user's* documents is a rejection on ownership, not a lookup — and because that check authorizes, it fails closed (rule 10). An injected instruction saying "read document 7" must die on ownership, not on the model politely declining.

The line that does not move: **no tool with side effects.** No writes, no network, no email, no publishing. That is [../security/prompt-injection.md](../security/prompt-injection.md)'s Defense 5, and the tools above do not approach it.

### The prompt contract

The build prompt states, in order of importance:

1. Output valid `Scene` JSON, nothing else
2. Use only copy derived from `keyMessages` and `proofPoints` — invent nothing
3. Never emit colors, sizes, fonts, durations, or easing — those don't exist in your vocabulary
4. Respect character limits; they are hard
5. Prefer fewer blocks. A scene with two blocks usually beats one with six

**Point 3 is enforced by omission first, and by rejection always.** The schema handed to the model has no field where a hex code would fit — so on a route that enforces schemas natively there is nowhere to put one, and on every route the model is not being asked to resist a temptation the vocabulary never offered. Don't describe what not to do; leave out the place to do it. What *guarantees* it is the schema parse and the presentational-value check, immediately below.

### Validation: one gate, and a decoder that only shifts the odds

An earlier draft of this document drew a hard line between constraints the decoder made *unrepresentable* and constraints the schema rejected after the fact. **Routing through a provider-neutral seam collapses that distinction, and it is better to state it plainly than to keep a guarantee that no longer holds.**

| Constraint | Enforced by | Reality |
|---|---|---|
| Shape — which fields exist, which types, which enums | **Pydantic, after the response.** The decoder helps *if* the route enforces schemas natively | Usually correct. Not guaranteed — enforcement varies by provider and by endpoint, and endpoint support changes over time |
| **Character caps** — `Headline ≤ 60`, `Body ≤ 240` | **Pydantic, after the response.** JSON Schema `minLength`/`maxLength` are widely unsupported by structured-output implementations regardless of route | Fails often. Triggers the repair loop |
| Semantic rules — one `Headline` per scene, region validity, claim provenance | Pydantic validators + post-build checks | Occasionally |

**The schema parse was always the real gate.** Decoder enforcement was a cost and reliability optimization — it lowers how *often* the model emits something invalid. It was never what stopped invalid output from reaching a page. Output that fails the parse is rejected, repaired once, and then fails visibly.

Two consequences worth internalizing:

1. **A hex code is no longer structurally unrepresentable — it is reliably rejected.** The security claim in [../security/prompt-injection.md](../security/prompt-injection.md) restates from *"a compromised model can only emit valid Scene JSON"* to *"a compromised model can only cause a rejected generation."* Same outcome, different route — and the no-styling regex check in [spec.md](spec.md) matters more now, not less. It is the thing that catches what the decoder was previously assumed to prevent.
2. **State every budget in the prompt as a hard number.** Prompting is the only portable lever on output length, and it is what actually reduces repair frequency. Keep the length constraint on the Pydantic field anyway — it costs nothing and it is what does the rejecting.

**The repair rate is the number that decides whether this trade was right** ([../techstack/decisions.md](../techstack/decisions.md)). It is recorded per phase and per model in `generations`. If Build's repair rate is materially worse than a direct vendor call, point that one phase at a single provider — the seam stays, only its routing changes, and nothing else in the pipeline moves. That is the entire reason the seam exists.

### Repair and refusal

Every scene is Pydantic-validated on return. Invalid → one repair call containing the scene, the specific errors, and nothing else. Still invalid → surface the failure honestly. Do not silently drop the scene, and do not retry forever.

**A refusal is not an error status, and the seam must not let it look like success.** Models decline requests with a *successful* HTTP response whose content is empty or partial — the field that says so differs by provider, which is exactly why it is normalized in one place. Code that reads the first content block unconditionally crashes on the first refusal.

```ts
// in the seam, not at every call site
if refusal := detect_refusal(raw):
    return err(Refused(detail=refusal))
```

Marketing copy rarely trips a safety classifier. **Imported source material is arbitrary user content**, so Intake is where this fires, and a refusal there must reach the user as a refusal rather than as a validation failure they cannot act on.

**Log every repair.** The pattern of what fails is the highest-signal data the product produces: it tells you exactly where the schema and the prompt disagree. Log the error class, never the content ([../techstack/backend.md](../techstack/backend.md)).

### Prompt caching — the single biggest cost lever, and it varies by route

Across a 12-scene build, the system prompt, schema, brief, brand kit, and outline are **byte-identical on every call**. Only the scene-specific instruction changes. Caching that shared prefix is the difference between paying for it once and paying for it twelve times.

**What is portable is the discipline; what varies is the mechanism.** Caching is a prefix match everywhere — one byte anywhere in the prefix invalidates everything after it — so these three rules hold on every route:

- **Never interpolate a timestamp, UUID, or scene index into the system prompt.** They sit at the front and invalidate the whole prefix.
- **Serialize the schema deterministically** — sorted keys, stable ordering. A re-ordered JSON dump is a different prefix.
- **Put the scene-specific instruction last**, after everything shared.

What the seam has to absorb, because getting it wrong silently costs 10× on the largest phase:

| | Varies how |
|---|---|
| **Activation** | Some providers cache automatically with no configuration. Others cache **nothing** unless you mark explicit breakpoints on the content blocks you want cached |
| **Discount** | Cache reads bill at roughly **0.1× to 0.5×** depending on provider — a 5× spread on the same optimization |
| **Write premium** | A cache write typically costs **1.25×–2×** a normal input token. Caching a prefix used once is a loss |
| **Minimum cacheable prefix** | Roughly **1,024 to 4,096 tokens**, model-dependent. A realistic build prefix clears even the high end; a Director or Edit prefix may not |

That last row is why caching is a Build optimization specifically. Edit calls are small, cheap, and frequent — the prefix may sit under the threshold, and a cache write premium on a prefix that never gets reused makes them *more* expensive.

**Verify it, per route, rather than assuming it.** Cached-token counts should be non-zero from the second scene onward. Zero across a whole build means either a silent invalidator in the prefix or a route that never had caching enabled — and the two look identical on the invoice.

### Parallel scene builds have a caching trap

Scenes are independent, so building them in parallel is tempting. But **a cache entry only becomes readable once the first response begins streaming** — fire 12 concurrent requests with the same prefix and all 12 pay full price, because none can read what the others are still writing.

The fix costs one round trip: **send scene 1, await its first streamed token, then fire the remaining 11.** They read the cache scene 1 just wrote. This also happens to match the streaming UX — scene 1 appears first anyway.

---

## Phase 4 — Edit

**In:** one block + its scene context + a user instruction. **Out:** `Partial<BlockProps>`.

```ts
{ sceneId, blockId, props: { text: "..." } }
```

The smallest call in the system. It sees one block, returns patched props, and cannot touch anything else — "make this headline punchier" structurally cannot restyle the page or rewrite a neighbor.

Property-panel edits produce the identical patch shape, so there is one code path and one place validation lives. Re-validate the tree after every patch — against the current art direction's budgets, which is what makes this the same mechanism v2's reskin uses ([../v2/transformations.md](../v2/transformations.md)).

One tier-0 tool: `read_block(id)`, returning the block's current props so an edit is a diff rather than a rewrite.

---

## Imagery

The build phase never emits an image URL. It emits an `Image` block whose `assetId` points at an `Asset`, and assets arrive two ways:

**Uploads** — the user's own product shots, screenshots, photography. Preferred whenever they exist. A launch experience showing the real product beats a generated approximation every time. Selection is by id from `list_assets()`, so the model chooses among what the user supplied and cannot reference an asset that does not exist.

Every upload is verified and re-encoded in the fetch worker before it is servable ([../techstack/infrastructure.md](../techstack/infrastructure.md)) — magic-byte checks, dimension caps before decode, EXIF stripped. An asset reaches the pipeline only after that, which is why the pipeline can treat asset metadata as trusted.

**Generated** — a separate call, after the scene tree exists, for scenes the build phase marked as needing imagery it had no asset for. The prompt is derived from the scene's copy and the art direction's visual language, and the result is stored as an `Asset` with `source: 'generated'`.

Three rules, all learned from the wedge rather than from taste:

1. **Never generate the product.** Generated product imagery is a legal and credibility problem, not a quality one. Generate atmosphere, texture, and abstract environment — never the thing being sold.
2. **Prefer `AbstractVisual` first.** It costs nothing, is always on-brand, and is regenerable from a seed. Reach for image generation only when a scene needs photographic depth that code cannot supply.
3. **Mark it.** `source: 'generated'` is visible in the editor. A marketer must know what is real before they publish.

---

## What an experience actually costs

**A worked example on one frontier route, not a fixed price.** At roughly $5/$25 per MTok in/out — mid-range for a frontier model in 2026 — a representative 8-scene experience comes to:

| Phase | Calls | Input | Output | Cost |
|---|---|---|---|---|
| Intake | ~3 | ~4.5K | ~0.9K | ~$0.05 |
| Director | 1 | ~2K | ~0.6K | ~$0.03 |
| **Build** (uncached) | 8 | ~26K | ~4K | ~$0.23 |
| **Build** (cached) | 8 | ~8K effective | ~4K | ~$0.14 |
| Edit | per edit | ~1.2K | ~0.15K | ~$0.01 |

**A complete experience costs roughly $0.20–0.25 in model tokens**, and **roughly $0.40 once v2's visual verification loop is on** — a render and a vision call per scene ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)). Even at five times either estimate it is under $1.50.

Routing changes the number substantially in both directions: a budget model on Director and Edit costs cents, and the caching spread alone is 5× on the largest phase. **The conclusion survives all of it.**

> **Token cost is not the constraint on this product.** Generated imagery, storage, bandwidth, and human review time all exceed it.

That settles something the roadmap left open. Pricing is deferred to v3 by design, and this is the evidence that deferring it was safe — a free tier that hands out generation is not the existential risk it would be if a build cost $5. It is also why the visual loop is *not* a cost decision: doubling a rounding error to catch layout defects a schema structurally cannot see is the easiest trade in the document.

**Instrument rather than trust this table.** `generations` records tokens and calls per phase — both, because some providers now bill task quotas rather than tokens, and cost accounting that assumes per-token billing will eventually mismeasure ([../techstack/ai-stack.md](../techstack/ai-stack.md)).

## Model notes

**There is no default model, and that is a decision rather than an omission** ([../techstack/ai-stack.md](../techstack/ai-stack.md)). Any model named here would be wrong within two quarters. What is fixed is the interface — a prompt and a Pydantic schema in, conforming JSON out — and the apparatus for choosing what sits behind it.

Four criteria decide, in this order:

1. **Schema conformance**, measured as the repair rate. The single number that determines whether a model is usable here. Measure it per model *and per route*
2. **Design judgment under constraint** — layout, emphasis, motion intent, copy inside a budget. Correlates poorly with coding and reasoning benchmarks. The only way to know is to look at rendered output
3. **Vision quality**, for v2's visual loop and v3's derivation. A distinct capability that may warrant a distinct model
4. **Cost, last.** See above

> **Spend on Build, economise everywhere else, and let evals decide where the line falls.**

Build carries the quality of the entire product and is the last place to economize. Director and Edit are small structured tasks where a cheaper model plausibly holds up — and the table above shows the saving is cents, so measure before trading quality for it.

Two mechanics that stay true on any route:

- **Ask for structured output, not JSON parsed out of prose.** Fewer repair loops even where the schema is only a strong hint.
- **Stream long requests.** Non-streaming calls hit HTTP timeouts, and streaming is what the per-scene UX wants anyway.

## Where the pipeline runs

In v1, all of it runs in the dev server, because v1 is a single user on Docker Compose with no AWS account at all ([../techstack/infrastructure.md](../techstack/infrastructure.md)).

From v3 the phases split across runtimes on the trust boundary ([../techstack/backend.md](../techstack/backend.md)):

| | Where | Why |
|---|---|---|
| Intake, Director, Build, Edit | **`api`** | Interactive, latency-sensitive, streams to the editor |
| Document extraction, URL fetching | **Fetch worker** | Hostile input, and it holds nothing worth stealing |
| Transcreation, posters, scheduled work | **`jobs`** | Long-running, needs the database, never sees hostile input |
| Publishing, and the visual verification loop (v2+) | **`render`** | Needs the renderer and a browser together, and a validated scene tree is trusted input. `jobs` orchestrates it; `render` performs it |

**No prompts, no outputs, no brief content reach a log**, in any of them. `generations` holds phase, token and call counts, the repair flag, an error class, and a duration — enough to answer what it costs and which rules fail most, and nothing that would put a customer's embargoed launch messaging in an error tracker ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)).

## Open questions

- **Parallel vs sequential build.** Parallel is faster; sequential lets each scene see the previous one and avoid repeating a layout. Probably: parallel with the cache-warming first call above, and layout assignment decided by the director so repetition is prevented upstream.
- **Regeneration of a single scene.** Clearly needed, but does it re-read neighbors for consistency? Resolve when the editor is built.
- **Where `AbstractVisual` seeds come from.** Random per generation means a regenerated scene looks different for no reason. Probably derive from scene id.
