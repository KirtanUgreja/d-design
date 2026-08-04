# Phase 07 — Director

> One cheap call turning a Brief into an editable outline, and the human gate that makes every downstream token worth spending. The smallest phase in the pipeline and the one that saves the most money.

**Depends on:** [06](06-model-seam-and-build.md) · **Blocks:** [08](08-intake.md) is independent; the end-to-end run needs both · **Spec step:** 6

---

## Search

**Read first**

- [../ai-pipeline.md](../ai-pipeline.md) → "Phase 2 — Director" and "Why four phases and not one"
- [../../security/prompt-injection.md](../../security/prompt-injection.md) → Defense 4, the outline gate
- [../scene-schema.md](../scene-schema.md) → `SceneIntent`, and why it is five values

**Grep for**

- `src/schema/outline.ts` — the `Outline` shape already exists from phase 01. Do not redefine it next to the Director
- `src/lib/ai/complete.ts` — the seam. Director is a `phase: 'director'` call and nothing more. It gets no retry of its own, no parse of its own, no metering of its own
- `src/features/generation/prompts/` — prompts live together, in the repo, reviewed in the diff

**Verify externally** — nothing. This is the phase with the fewest unknowns, which is why it is a good one to build immediately after the seam.

---

## Make

```
src/features/director/
  index.ts
  direct.ts                Brief → Outline, one call, no tools
  prompts/director.ts
  outline-editor.tsx       the gate: reorder, delete, retitle, change intent, add
  director.test.ts
```

### The call

**In:** `Brief`. **Out:** `Outline`. One call, no tools.

```ts
Outline {
  title: string;
  scenes: { intent: SceneIntent; beat: string; layoutHint?: Layout }[]
}
```

`beat` is one sentence describing what the scene *does* in the narrative — not its copy. The director decides structure and pacing, nothing else. Copy is the Build phase's job and mixing them here produces an outline nobody can evaluate.

**No tools, deliberately.** A pure transform on human-approved content with a human gate immediately after. There is nothing to look up and nothing to verify; adding a tool here would be tools for their own sake ([../../techstack/pipeline-tools.md](../../techstack/pipeline-tools.md)).

Rules, enforced by Pydantic on the `Outline` schema: 3–12 scenes · exactly one `hook`, first · at least one `cta` · **no repeated adjacent intents**.

**Assign `layoutHint` here, not in Build.** The open question in [../ai-pipeline.md](../ai-pipeline.md) — parallel versus sequential builds — resolves in favour of parallel *because* layout assignment happens upstream. A director that hands each scene a layout prevents the repetition a sequential build would have prevented by letting each scene see the last one, and it does it for one call instead of eleven round trips.

### The gate is the product decision

The outline renders as an editable list: reorder, delete, retitle, change intent, add a scene. **Build cannot run until the user approves.** Not a soft nudge, not a default-yes dialog — an actual gate.

It earns its place three times over:

| | |
|---|---|
| **Cost** | The expensive call only ever runs against a structure the user already accepted |
| **Quality** | Fixing a wrong narrative here is cheap. Fixing it after twelve scenes are built is a regeneration |
| **Security** | An injection that hijacks the outline — *"add a scene urging readers to visit…"* — is visible to a human before any page exists ([../../security/prompt-injection.md](../../security/prompt-injection.md), Defense 4) |

It does **not** catch a subtly rewritten proof point. That is what claim provenance in phase 06 is for, and the two are not substitutes.

### What the gate looks like, and why that is not a detail

Nobody else in this category has an approval step, so there is no convention to copy and the default — a bulleted list with a Continue button — reads as a form standing between the user and the thing they want. It is one of the four screens [../../design/app.md](../../design/app.md) budgets real design attention for, and it is hot for **trust** rather than for delight.

| | |
|---|---|
| **Scene cards, not a list** | The next screen is spatial. This one should already feel spatial |
| **Regenerate the outline is cheap and prominent** | It is the entire reason the gate sits before the expensive call. Hiding it wastes the gate |
| **Approve is the only high-emphasis control on the screen** | |
| **Claim provenance is shown here** | Which lines came from the user's `keyMessages` and which the director produced. This is the correct place for it — the editor is too late and too busy — and it is the trust feature competitors do not have ([../spec.md](../spec.md), Risk 2) |
| **Time as a range, never a percentage** | A percentage on a non-deterministic process is a number you will have to defend |
| **No skip, in v1** | If approval rates sit near 100%, that is a finding about the director, not a reason to remove the gate |

None of this changes the function boundary that actually enforces the gate. The UI is not the control — that is asserted below — but a control users route around resentfully is a control with a short life.

### Cost note

The Director prefix is small and the call runs once. **Caching it is probably a loss** — a cache write typically costs 1.25×–2× a normal input token, and a prefix used once never earns that back. Verify against the route's minimum cacheable prefix before enabling it here; this is the phase where the caching discipline that helps Build actively hurts.

---

## Verify

**The gate** — green.

**Outline rules**

- [ ] Pydantic rejects: fewer than 3 scenes · more than 12 · zero `hook` · two `hook`s · a `hook` that is not first · zero `cta` · two adjacent scenes with the same intent
- [ ] The 5 golden briefs each produce a valid `Outline` on the first call
- [ ] Every scene has a `layoutHint`, and adjacent scenes do not repeat one

**The gate itself**

- [ ] Build **cannot** be invoked without an approved outline. Assert it at the function boundary, not in the UI — the UI is not the control
- [ ] Reorder, delete, retitle, change intent, and add all produce a valid `Outline`
- [ ] Dragging a non-`hook` scene into first position is refused rather than silently rewriting intents. [01](01-scene-schema.md) resolved this: `intent` describes what a scene does, not where it sits, and the only positional rule is that the hook is first

**Security**

- [ ] An injection payload in the Brief that tries to add a scene shows up **in the outline, visibly**, before anything is built. That is the control working, not failing
- [ ] Director calls carry the same metering as Build — phase, model, route, tokens, calls, duration, no content

**Quality — measured, never gating**

- [ ] Read all five outlines. Do they read as narratives or as lists of topics? This is judgment and belongs to you, not to a judge model. Log the impression; do not automate it in v1

---

## Skipped

| Not built | Trigger |
|---|---|
| Tools for the Director | Nothing to look up. Adding one would be tools for their own sake |
| Multiple outline candidates to choose between | Tempting and it doubles the cheapest call in the pipeline. Revisit if users routinely reject the first outline — that rejection rate is the trigger, and it is worth logging |
| Prompt caching on this phase | The prefix may sit under the route's minimum and the write premium makes a single-use cache a loss. Measure before enabling |
| Regenerating a single scene from the outline | Phase 09 territory, and it needs the editor's context |

---

## Exit gate

- [ ] Brief → Outline works on all five golden briefs
- [ ] Every outline rule has a rejection test
- [ ] The approval gate is enforced at the function boundary, not only in the UI
- [ ] `layoutHint` is assigned by the director, so parallel builds do not produce repetitive layouts
- [ ] An injected outline hijack is visible to a human before any build runs
