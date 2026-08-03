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

One call per scene, in parallel where dependencies allow. Each call receives the full outline as context so scenes know their neighbors, and returns exactly one `Scene` conforming to [scene-schema.md](scene-schema.md).

Streaming per scene matters for perceived speed: the user watches the experience assemble instead of staring at a spinner, and can abort a bad direction on scene 2 rather than paying for 12.

### The prompt contract

The build prompt states, in order of importance:

1. Output valid `Scene` JSON, nothing else
2. Use only copy derived from `keyMessages` and `proofPoints` — invent nothing
3. Never emit colors, sizes, fonts, durations, or easing — those don't exist in your vocabulary
4. Respect character limits; they are hard
5. Prefer fewer blocks. A scene with two blocks usually beats one with six

Point 3 is best enforced by omission: the schema given to the model has no field where a hex code would fit. Don't describe what not to do — make it unrepresentable.

### Validation and repair

Every scene is Zod-validated on return. Invalid → one repair call containing the scene, the specific errors, and nothing else. Still invalid → surface the failure honestly. Do not silently drop the scene, and do not retry forever.

Expect the character caps to trip the repair loop frequently at first. That is the system working as designed — restraint enforced mechanically instead of requested politely.

**Log every repair.** The pattern of what fails is the highest-signal data the product produces: it tells you exactly where the schema and the prompt disagree.

---

## Phase 4 — Edit

**In:** one block + its scene context + a user instruction. **Out:** `Partial<BlockProps>`.

```ts
{ sceneId, blockId, props: { text: "..." } }
```

The smallest call in the system. It sees one block, returns patched props, and cannot touch anything else — "make this headline punchier" structurally cannot restyle the page or rewrite a neighbor.

Property-panel edits produce the identical patch shape, so there is one code path and one place validation lives. Re-validate the tree after every patch.

---

---

## Imagery

The build phase never emits an image URL. It emits an `Image` block whose
`assetId` points at an `Asset`, and assets arrive two ways:

**Uploads** — the user's own product shots, screenshots, photography. Preferred
whenever they exist. A launch experience showing the real product beats a
generated approximation every time.

**Generated** — a separate call, after the scene tree exists, for scenes the
build phase marked as needing imagery it had no asset for. The prompt is derived
from the scene's copy and the art direction's visual language, and the result is
stored as an `Asset` with `source: 'generated'`.

Three rules, all learned from the wedge rather than from taste:

1. **Never generate the product.** Generated product imagery is a legal and
   credibility problem, not a quality one. Generate atmosphere, texture, and
   abstract environment — never the thing being sold.
2. **Prefer `AbstractVisual` first.** It costs nothing, is always on-brand, and
   is regenerable from a seed. Reach for image generation only when a scene needs
   photographic depth that code cannot supply.
3. **Mark it.** `source: 'generated'` is visible in the editor. A marketer must
   know what is real before they publish.

## Cost shape

| Phase | Calls | Relative cost |
|---|---|---|
| Intake | 1–5 (conversational) | low |
| Director | 1 | very low |
| Build | 1 per scene | **~90% of total** |
| Edit | 1 per edit | negligible |

Two consequences worth designing around: the outline gate exists to stop bad builds before they happen, and surgical edits mean iteration is nearly free — which is the entire reason a user picks this over regenerating in a chat window.

Pricing is deliberately deferred until these numbers are measured rather than guessed. Instrument token usage per phase from the first working build.

## Model notes

Director and Edit are small structured tasks — a fast model is appropriate. Build carries the quality of the entire product and should use the strongest available model; it is the last place to economize.

Use structured output / tool-calling to constrain responses to the schema rather than parsing JSON out of prose. Fewer repair loops, lower cost, less to go wrong.

## Open questions

- **Parallel vs sequential build.** Parallel is faster; sequential lets each scene see the previous one and avoid repeating a layout. Probably: parallel, with layout assignment decided by the director so repetition is prevented upstream.
- **Regeneration of a single scene.** Clearly needed, but does it re-read neighbors for consistency? Resolve when the editor is built.
- **Where `AbstractVisual` seeds come from.** Random per generation means a regenerated scene looks different for no reason. Probably derive from scene id.
