# AI Pipeline

Four calls, not one. Each phase has a typed input, a typed output, and a validation gate.

```
Intake ──▶ Brief ──▶ Director ──▶ Outline ──▶ [user approves] ──▶ Build ──▶ Scene tree
                                                                              │
                                                                      Edit ◀──┘
```

## Why four phases and not one

A single "prompt → finished experience" call is the most impressive demo and the worst product. It burns the most tokens on results users reject, gives no intervention point, and makes every subsequent edit a regeneration.

Splitting it means the expensive call only runs against a structure the user already approved, and edits cost roughly 1% of a build.

---

## Phase 1 — Intake

**In:** conversation, an uploaded document, or a URL. **Out:** `Brief`.

```ts
Brief {
  goal: string;              // what this experience must achieve
  audience: string;
  keyMessages: string[];     // 3-5, APPROVED copy — see below
  proofPoints: string[];     // stats, quotes, customer names
  tone: string;
  cta: { label: string; href: string };
  assets: AssetRef[];
  constraints?: string;      // legal, brand, must-not-say
}
```

Three entry paths, one output shape:

- **Import** — PDF, deck, doc, or URL. Extract, then ask only about what's missing.
- **Prompt** — freeform description. Fill what's inferable, ask about the rest.
- **Q&A** — no material at all. The AI interviews the user.

Always ask, never assume: `goal`, `audience`, `cta`. These three determine narrative structure, and guessing them wastes the entire downstream pipeline.

### Reading the uploaded document

PDFs go in as a `document` content block, placed **before** the text block in the same user message:

```python
{"type": "document",
 "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
```

Limits: 32 MB per request, 600 pages. Base64 must contain no newlines. For a deck a user will reference across several intake turns, upload once via the Files API (beta header `files-api-2025-04-14`) and reference by `file_id` instead of re-sending bytes every turn.

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

```ts
Outline {
  title: string;
  scenes: { intent: SceneIntent; beat: string; layoutHint?: Layout }[]
}
```

`beat` is one sentence describing what this scene does in the narrative — not its copy. The director decides *structure and pacing*, nothing else.

Rules: 3–12 scenes · exactly one `hook`, first · at least one `cta` · no repeated adjacent intents.

**This is the user gate.** The outline renders as an editable list: reorder, delete, retitle, change intent, add a scene. Cheap for the user to fix a wrong narrative here; expensive after 12 scenes are built.

---

## Phase 3 — Build

**In:** `Brief` + approved `Outline` + `BrandKit`. **Out:** `Scene[]`, streamed one scene per call.

One call per scene. Each call receives the full outline as context so scenes know their neighbors, and returns exactly one `Scene` conforming to [scene-schema.md](scene-schema.md).

Streaming per scene matters for perceived speed: the user watches the experience assemble instead of staring at a spinner, and can abort a bad direction on scene 2 rather than paying for 12.

### The request

```python
client.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    output_config={
        "format": {"type": "json_schema", "schema": SCENE_SCHEMA},
        "effort": "high",
    },
    cache_control={"type": "ephemeral"},
    system=[{"type": "text", "text": BUILD_SYSTEM_PROMPT}],
    messages=[{"role": "user", "content": scene_request}],
)
```

Notes that matter:

- **`output_config.format`, not `output_format`.** The top-level `output_format` parameter is deprecated API-wide.
- **Thinking is on by default** on Opus 5 — omitting the `thinking` parameter runs adaptive. This is a change from Opus 4.8/4.7, where omitting it meant no thinking, and `max_tokens` caps thinking *plus* response text together. Size `max_tokens` with that in mind.
- **`effort` lives inside `output_config`**, not at the top level. Default is `high`.
- **No `temperature` / `top_p` / `top_k`.** These are removed on Opus 5 and return a 400. Steer with prompting.

### The prompt contract

The build prompt states, in order of importance:

1. Output valid `Scene` JSON, nothing else
2. Use only copy derived from `keyMessages` and `proofPoints` — invent nothing
3. Never emit colors, sizes, fonts, durations, or easing — those don't exist in your vocabulary
4. Respect character limits; they are hard
5. Prefer fewer blocks. A scene with two blocks usually beats one with six

Point 3 is best enforced by omission: the schema given to the model has no field where a hex code would fit. Don't describe what not to do — make it unrepresentable.

### Validation is two layers, and only one is enforced by the decoder

This distinction matters and is easy to get wrong.

| Constraint | Enforced by | When it fails |
|---|---|---|
| Shape — which fields exist, which types, which enums | **The decoder.** Structured outputs constrains generation, so a hex code has nowhere to go | Cannot fail. The token is unrepresentable |
| **Character caps** — `Headline ≤ 60`, `Body ≤ 240` | **Zod, after the response.** JSON Schema `minLength`/`maxLength` are **not supported** by structured outputs | Fails often. Triggers the repair loop |
| Semantic rules — one `Headline` per scene, region validity, claim provenance | Zod + post-build checks | Occasionally |

**The consequence:** an earlier framing of this design claimed length caps make the model "unable to produce valid output unless it is concise." That is true of the *shape* constraints and false of the *length* ones. Length is enforced by rejection and repair, not by constrained decoding — the model can and will emit a 90-character headline, and the loop sends it back.

Both still produce mechanical restraint rather than politely-requested restraint. The difference is cost: shape violations are free to prevent, length violations cost a repair call. So **state the character budget in the prompt as a hard number**, because that is what reduces repair-loop frequency — the schema won't do it for you.

The Python and TypeScript SDKs strip unsupported constraints from the schema before sending and validate them client-side, so leaving `maxLength` in your Zod schema is harmless — just don't expect it to constrain generation.

### Repair and refusal

Every scene is Zod-validated on return. Invalid → one repair call containing the scene, the specific errors, and nothing else. Still invalid → surface the failure honestly. Do not silently drop the scene, and do not retry forever.

**Check `stop_reason` before reading `content`.** Opus 5 ships elevated safety classifiers that can decline a request with HTTP 200 and `stop_reason: "refusal"` — `content` is empty or partial, so code that reads `content[0]` unconditionally crashes. Marketing copy rarely trips them, but imported source material is arbitrary user content.

```python
if response.stop_reason == "refusal":
    surface_to_user(response.stop_details)   # stop_details may be null — guard it
```

**Log every repair.** The pattern of what fails is the highest-signal data the product produces: it tells you exactly where the schema and the prompt disagree.

### Prompt caching — the single biggest cost lever

Across a 12-scene build, the system prompt, schema, brief, brand kit, and outline are **byte-identical on every call**. Only the scene-specific instruction changes. Put the cache breakpoint at the end of that shared prefix and the repeated portion bills at ~0.1× instead of 1×.

Caching is a **prefix match** — one byte anywhere in the prefix invalidates everything after it. Three rules follow:

- **Never interpolate a timestamp, UUID, or scene index into the system prompt.** They sit at the front and invalidate the whole prefix.
- **Serialize the schema deterministically** — sorted keys, stable ordering. A re-ordered JSON dump is a different prefix.
- **Put the scene-specific instruction last**, after the breakpoint.

Verify it worked: `usage.cache_read_input_tokens` should be non-zero from the second scene onward. If it's zero across a whole build, a silent invalidator is in the prefix.

Minimum cacheable prefix on Opus 5 is **512 tokens** — half the Opus 4.8 threshold, and any realistic build prefix clears it easily.

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

Property-panel edits produce the identical patch shape, so there is one code path and one place validation lives. Re-validate the tree after every patch.

---

## Imagery

The build phase never emits an image URL. It emits an `Image` block whose `assetId` points at an `Asset`, and assets arrive two ways:

**Uploads** — the user's own product shots, screenshots, photography. Preferred whenever they exist. A launch experience showing the real product beats a generated approximation every time.

**Generated** — a separate call, after the scene tree exists, for scenes the build phase marked as needing imagery it had no asset for. The prompt is derived from the scene's copy and the art direction's visual language, and the result is stored as an `Asset` with `source: 'generated'`.

Three rules, all learned from the wedge rather than from taste:

1. **Never generate the product.** Generated product imagery is a legal and credibility problem, not a quality one. Generate atmosphere, texture, and abstract environment — never the thing being sold.
2. **Prefer `AbstractVisual` first.** It costs nothing, is always on-brand, and is regenerable from a seed. Reach for image generation only when a scene needs photographic depth that code cannot supply.
3. **Mark it.** `source: 'generated'` is visible in the editor. A marketer must know what is real before they publish.

---

## What an experience actually costs

Opus 5 is $5 / $25 per MTok (input / output). For a representative 8-scene experience:

| Phase | Calls | Input | Output | Cost |
|---|---|---|---|---|
| Intake | ~3 | ~4.5K | ~0.9K | ~$0.05 |
| Director | 1 | ~2K | ~0.6K | ~$0.03 |
| **Build** (uncached) | 8 | ~26K | ~4K | ~$0.23 |
| **Build** (cached) | 8 | ~8K effective | ~4K | ~$0.14 |
| Edit | per edit | ~1.2K | ~0.15K | ~$0.01 |

**A complete experience costs roughly $0.20–0.25 in model tokens.** Even at five times this estimate, it is under $1.50.

That number is worth internalizing, because it settles something the roadmap left open: **token cost is not the constraint on this product.** Generated imagery, storage, bandwidth, and human review time all exceed it. Pricing is deferred to v3 by design, and this is the evidence that deferring it was safe — a free tier that hands out generation is not the existential risk it would be if a build cost $5.

Instrument it anyway. The `generations` table records tokens per phase; measure rather than trust this table.

## Model notes

**Default to `claude-opus-5` for every phase.** Build carries the quality of the entire product and is the last place to economize. Director and Edit are small structured tasks where a smaller model — `claude-sonnet-5` at $3/$15, or `claude-haiku-4-5` at $1/$5 — may hold up, but the numbers above show the saving is cents. Measure before trading quality for it.

Two mechanics to get right:

- **Use structured outputs, not JSON-parsed-from-prose.** Fewer repair loops, lower cost, less to go wrong.
- **Stream any request with `max_tokens` above ~16K.** Non-streaming requests hit SDK HTTP timeouts; the SDK will refuse the request outright if it estimates over ~10 minutes.

## Open questions

- **Parallel vs sequential build.** Parallel is faster; sequential lets each scene see the previous one and avoid repeating a layout. Probably: parallel with the cache-warming first call above, and layout assignment decided by the director so repetition is prevented upstream.
- **Regeneration of a single scene.** Clearly needed, but does it re-read neighbors for consistency? Resolve when the editor is built.
- **Where `AbstractVisual` seeds come from.** Random per generation means a regenerated scene looks different for no reason. Probably derive from scene id.
