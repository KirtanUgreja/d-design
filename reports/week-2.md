# Week 2 — The AI pipeline: model seam, Build, Director, Intake

**Dates:** Mon 11 Aug – Sun 17 Aug 2026 · **Status:** Phases 06–08 complete

## What was done this week

Week 1 proved the runtime — a typed scene tree that renders beautifully. Week 2 added the brain: the four-phase AI pipeline that turns a conversation into a published experience, with a human gate in the middle. Every call goes through **one provider seam**; the product has no preferred model vendor.

The pipeline shape, four calls not one:

```
Intake ──▶ Brief ──▶ Director ──▶ Outline ──▶ [user approves] ──▶ Build ──▶ Scene tree
                                                                             │
                                                                     Edit ◀──┘
```

### 1. Phase 06 — The model seam and the Build phase
- Built one provider abstraction that every model call goes through, so swapping models is a configuration change rather than a rewrite.
- Built the Build phase: the call that turns an approved outline into a full scene tree, streaming scenes to the browser.
- Ran the phase live and fixed the real defects it surfaced — schema-compatibility bugs, a model switch, and the CI eval gate.
- Fixed the CI eval step (promptfoo's CLI flag had changed), serialized the eval worker, fixed the SSE framing bug that was killing builds, and fixed the eval timeout.

### 2. Phase 07 — The Director phase
- Built the Director: the call that turns a `Brief` into an editable `Outline` before anything expensive happens.
- The human gate sits between Director and Build — bad directions are killed before the expensive call runs, and edits cost roughly 1% of a build.
- Enforced a prompt-leak check in the pipeline itself, not just in the evals.
- Fixed the eval harness leaking its database pool across loops.

### 3. Phase 08 — Intake (API half)
- Built the Intake phase: three entry paths, one output shape.
  - **Import** — PDF, deck, doc, or URL. Extract, then ask only about what's missing.
  - **Prompt** — freeform description. Fill what's inferable, ask about the rest.
  - **Q&A** — no material at all. The AI interviews the user.
- Uploaded documents are parsed by an isolated worker before the model sees them — not by the model — with caps enforced before parsing (page count, byte size, decompression ratio).
- Recorded Intake's first live run.

### 4. The eval corpus
- Five golden briefs, seven injection payloads, four structural assertions — all passing.
- The seven injection payloads are the adversarial test: direct override, role confusion, exfiltration, href hijack, slot poisoning, encoding tricks, claim tampering.

## This week's deliverables
- The provider seam with a live Build phase and a live Director.
- Intake: conversation → `Brief`, with secure document handling in the isolated worker.
- A green eval corpus covering both correctness and prompt-injection resistance.
- The human approval gate between outline and build.

## Next week's plan
- Build the web half of Intake: the intake screen and the full product path.
- Fix two defects the live runs found: the provider truncating copy at its max length, and reasoning tokens eating `max_tokens` on repair.
- Build the editor — select, property panel, element-scoped prompt — the editing model that makes generated output adjustable.
- Build the brand kit and the upload surface, the only hostile-input surface in v1.
- Build the five visual generators and the Slot, then run the v1 acceptance run.
