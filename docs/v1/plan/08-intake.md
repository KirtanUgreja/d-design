# Phase 08 — Intake

> Conversation in, `Brief` out. The phase that captures *approved* messaging, and the one place a marketer's trust is won or lost before a single page exists.

**Depends on:** [06](06-model-seam-and-build.md) · **Blocks:** the end-to-end run · **Spec step:** 7

**Scope decision:** v1 ships **prompt and AI-led Q&A only**. The import path — PDF, deck, doc, URL — is deferred. See below; it is the plan's largest deliberate deviation from [../ai-pipeline.md](../ai-pipeline.md) and it is recorded rather than absorbed quietly.

---

## Search

**Read first**

- [../ai-pipeline.md](../ai-pipeline.md) → "Phase 1 — Intake", especially "The claims rule" and "The URL rule"
- [../../security/prompt-injection.md](../../security/prompt-injection.md) → the five paths, and which of them v1 actually opens
- [../../security/tenancy-and-data.md](../../security/tenancy-and-data.md) → what a brief is, legally and commercially, and therefore what must never be logged

**Grep for**

- `src/schema/brief.ts` — defined in phase 01, consumed here. One source
- `src/lib/ai/complete.ts` — Intake is `phase: 'intake'`. Refusal normalization already lives in the seam, and **Intake is where refusals actually fire**, because its input is arbitrary user content rather than marketing copy
- `src/features/generation/checks.ts` — the URL allowlist built in phase 06. The Brief's `cta.href` is validated by the same code, not by a second copy

**Verify externally** — nothing, given the deferred import path. That absence is most of the point.

---

## Make

```
src/features/intake/
  index.ts
  interview.ts          the Q&A loop → Brief
  prompts/intake.ts
  intake.data.ts        'server-only' — the briefs table
  intake.test.ts
```

### Why import is deferred

[../ai-pipeline.md](../ai-pipeline.md) specifies extraction running in the **fetch worker** — the container with no database, no VPC route, and nothing worth stealing — because an uploaded PDF is the single most hostile input in the product, and PDF parsers are the richest source of parser CVEs in the dependency tree.

That container is v3 infrastructure ([../../techstack/infrastructure.md](../../techstack/infrastructure.md)). The three available options were: build it early, run the parser in the app anyway, or defer the path. Running `pdf.js` and `sharp` next to the database credentials is exactly the placement [../../coderules/dependencies.md](../../coderules/dependencies.md) says *should feel wrong* — the ladder's fifth rung is "if it touches untrusted bytes, it goes in the fetch worker", and a feature that seems to need one elsewhere is a signal the work is in the wrong process.

So it waits. Two consequences worth being explicit about:

- **The `Brief` shape does not change.** Import produces the same object by a different route, so this is purely additive when the worker exists. No downstream phase knows the difference
- **v1 has no untrusted-input path at all.** Every byte reaching the model was typed by the single user. That is why phase 06's injection corpus runs against pasted text — which is still worth running, because the corpus has to exist and be green *before* the path that needs it opens

Record it as a `ponytail:` comment at the top of `interview.ts` naming the ceiling and the upgrade path.

### The three entry paths, minus one

| Path | v1 |
|---|---|
| **Prompt** — freeform description | **Yes.** Fill what is inferable, ask about the rest |
| **Q&A** — no material at all, the AI interviews | **Yes.** The default path |
| **Import** — PDF, deck, doc, URL | **Deferred.** Needs the fetch worker |

### Always ask, never assume

`goal`, `audience`, `cta`. These three determine narrative structure, and guessing them wastes the entire downstream pipeline — a wrong audience produces twelve well-built scenes aimed at the wrong person.

The interview may infer everything else. It may not infer these, even when it thinks it can.

### The claims rule — the most important constraint in the pipeline

```ts
Brief {
  goal, audience,
  keyMessages: string[],     // 3–5, APPROVED copy
  proofPoints: string[],     // stats, quotes, customer names
  tone,
  cta: { label, href },
  assets: AssetRef[],
  constraints?: string,      // legal, brand, must-not-say
}
```

`keyMessages` and `proofPoints` are **approved copy**. Downstream phases may shorten, split, and rearrange them. They may not invent new claims, new statistics, new customer names, or new capabilities.

A marketer cannot ship a page asserting something untrue about their product, and one such incident costs more trust than a hundred good generations earn ([../spec.md](../spec.md), Risk 2). Enforcement is three-layered — stated in the build prompt, visible at the outline gate, and checked after the build. **Only the third layer catches anything**, and it was built in phase 06.

The Intake UI's job here is narrow and important: make it obvious that what the user types into `keyMessages` is what will appear on the page. If the interview paraphrases the user's messaging into something smoother, it has already broken the rule the whole pipeline rests on.

### The interview is not a chat

The first screen a user touches, and one of the four that gets real design attention ([../../design/app.md](../../design/app.md)). Four decisions, each of which is cheaper to take now than to unwind:

| | |
|---|---|
| **Prompt box first, then a short structured interview** | Chat bubbles promise conversational memory, open-ended back-and-forth, and off-task requests — three things this pipeline will not do. A chat log is also not a `Brief`; a structured interview produces one directly |
| **Skipping to generate is always available** | The interview improves the output. It must never gate it |
| **The Brief stays visible and editable, permanently** | It is the approved-claims record. Burying it behind a step contradicts the rule above, which says the user's exact words are what ships |
| **No upload affordance at all** | Import is deferred, and a disabled button that explains why it is disabled is worse than no button. The `Brief` shape is unchanged when the fetch worker lands, so nothing has to move |

**No templates, no starting-point gallery.** "No templates" is the positioning ([../market.md](../market.md)); a template picker on the first screen argues against the product on the product's own front page. The equivalent affordance is example *briefs* — real launches — and every one of them should be commercial work, because generic examples recruit the cohort that killed Tome ([../../design/principles.md](../../design/principles.md), principle 2).

**The first run has a 90-second budget**, which is what makes the brand kit a second-session concern rather than a setup step. Six brand fields before anything has happened is where a first session is lost.

### The URL rule

`cta.href` comes from the user, always. The AI never composes a URL. Validate it here with the same scheme allowlist phase 06 uses — `javascript:`, `data:`, `vbscript:`, and protocol-relative all rejected — and store the full set of user-supplied URLs on the Brief, because that set is what phase 06's provenance check compares against.

### The `briefs` table

```
briefs  id, experience_id, owner_id, payload (jsonb), created_at
```

RLS policy and isolation test, same pattern as phase 00. `intake.data.ts` starts with `import 'server-only'`.

**The brief is stored; it is never logged.** It is the customer's unreleased launch messaging, and the distinction between a row in a table the user owns and a line in an error tracker is the whole of [../../security/tenancy-and-data.md](../../security/tenancy-and-data.md).

---

## Verify

**The gate** — green.

**Brief construction**

- [ ] `goal`, `audience`, and `cta` are always asked, never inferred. Assert it: a transcript that never mentions the audience must not produce a Brief with one
- [ ] `keyMessages` capped at 3–5 by Zod
- [ ] The Brief is Zod-parsed once, at entry, and trusted thereafter
- [ ] A user's exact `keyMessages` text survives into the Brief unmodified — if the interview smooths it, the claims rule is already broken

**URLs**

- [ ] `javascript:`, `data:`, `vbscript:`, and `//evil.example` in `cta.href` are all rejected
- [ ] The set of user-supplied URLs is stored on the Brief and is what phase 06's provenance check reads

**Refusals**

- [ ] A prompt that trips a safety classifier reaches the user **as a refusal**, not as a validation failure they cannot act on. This is the phase where refusals actually fire, and the seam's normalization is what makes it possible

**Privacy**

- [ ] `generations` rows for `phase: 'intake'` contain no brief content
- [ ] A canary string typed into the interview appears in the `briefs` table and **nowhere else** — not in logs, not in error output, not in `generations`

**Isolation**

- [ ] `briefs` has an RLS policy and an isolation test, same as every other table

---

## Skipped

| Not built | Trigger |
|---|---|
| Import — PDF, deck, doc | The fetch worker exists. Then: quarantine prefix → caps before parse (page count, byte size, decompression ratio) → magic bytes → `unpdf`/`pdf.js` → extracted text to the model |
| URL import | Same worker, plus the full SSRF suite. Network isolation, not URL filtering |
| `list_documents` / `read_document` tools | They exist to page a document safely, and there are no documents |
| Model-native PDF reading | The documented fallback for the day a parser advisory lands with no patch. Available immediately, costs tokens, needs the seam to expose native document input per provider |
| Multi-turn brief revision | Users edit the Brief directly. Add a conversational revision loop only if direct editing proves insufficient |

---

## Exit gate

- [ ] Prompt and Q&A both produce a valid `Brief`
- [ ] The three always-ask fields are enforced, not encouraged
- [ ] URL scheme allowlist shared with phase 06, not duplicated
- [ ] A refusal surfaces as a refusal
- [ ] Canary test proves brief content lives in exactly one place
- [ ] `ponytail:` comment on the deferred import path names the ceiling and the upgrade
