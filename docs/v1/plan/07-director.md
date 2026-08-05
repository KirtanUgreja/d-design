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

- [x] Pydantic rejects: fewer than 3 scenes · more than 12 · zero `hook` · two `hook`s · a `hook` that is not first · zero `cta` · two adjacent scenes with the same intent — `schema/test_outline.py`, one case per rule
- [x] The 5 golden briefs each produce a valid `Outline` on the first call. **Run live 2026-08-05** against `openai/gpt-5-mini` via `scripts/verify_director.py`, which runs every fixture in `evals/briefs/` through `direct_brief`: 5/5 returned an `Outline` and passed `check_outline`, with no failures. First-call by construction — `direct_brief` has no retry of its own, so a `Result` back is a first-call result. Shapes were 5 scenes (01, 02, 05) and 6 scenes (03, 04); 03 and 04 used `reveal` twice, non-adjacently, which is legal — the only positional rule is that the hook is first
- [x] Every scene has a `layoutHint`, and adjacent scenes do not repeat one — `features/director/checks.py`'s `check_outline`, tested in `test_checks.py`, and confirmed in the live run above (full-bleed → split-left → centered → grid → stack)

**The gate itself**

- [x] Build **cannot** be invoked without an approved outline. Assert it at the function boundary, not in the UI — the UI is not the control. `build_experience` takes `ApprovedOutline`, not `Outline`; `features/generation/test_build.py` proves the boundary is real at runtime, not only in mypy's eyes: a bare `Outline` fails with `AttributeError`, not a silent pass
- [x] Reorder, delete, retitle, change intent, and add all produce a valid `Outline` — `web/src/features/director/outline.ts`, 16 cases in `outline.test.ts`, exercised live through the real UI (see below)
- [x] Dragging a non-`hook` scene into first position is refused rather than silently rewriting intents. [01](01-scene-schema.md) resolved this: `intent` describes what a scene does, not where it sits, and the only positional rule is that the hook is first. Confirmed live: moving `problem` (index 1) into position 0 surfaced "exactly one scene has intent 'hook' and it is first" in the UI and left the order untouched

**Security**

- [x] An injection payload in the Brief that tries to add a scene shows up **in the outline, visibly**, before anything is built. That is the control working, not failing. True by construction, not by a dedicated adversarial corpus: Director and Build are two separate HTTP calls with no server-side chaining between them, and the client always renders the returned `Outline` for editing before a Build request can be sent — there is no code path where a Director response reaches Build without a human seeing it first. A dedicated injection corpus for Director (mirroring Build's `api/evals/injection/`) would still be worth building, but isn't what this control depends on
- [x] Director calls carry the same metering as Build — phase, model, route, tokens, calls, duration, no content. Confirmed live: the `generations` row for the test run above reads `phase='director', model_id='openai/gpt-5-mini', tokens_in=503, tokens_out=915, calls=1, repaired=false`, and nothing else

**Quality — measured, never gating**

- [ ] Read all five outlines. Do they read as narratives or as lists of topics? This is judgment and belongs to you, not to a judge model. Log the impression; do not automate it in v1. **All five are now generated and printable on demand** (`scripts/verify_director.py`), so the only thing outstanding is the human read — deliberately left unticked, because nothing but a person can tick it. This section never gates the exit gate

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

- [x] Brief → Outline works on all five golden briefs — run live 2026-08-05, 5/5 valid on the first call (see Verify). Repeatable as `uv run --env-file .env python -m scripts.verify_director`
- [x] Every outline rule has a rejection test
- [x] The approval gate is enforced at the function boundary, not only in the UI
- [x] `layoutHint` is assigned by the director, so parallel builds do not produce repetitive layouts
- [x] An injected outline hijack is visible to a human before any build runs

**Found live, fixed, not part of this phase's own scope — all in already-merged phase 06 code:**

- `ai/complete.py`'s `_iter_sse_data` framed SSE payloads on `httpx.aiter_lines()`, whose separator set includes three characters (`\x85`, `\u2028`, `\u2029`) that are legal *unescaped* inside a JSON string. A model writing one into its copy split its own payload in half and crashed the whole build with an unhandled `JSONDecodeError` rather than a `Result`. Reframed on `\n` alone — safe because a raw `\n` cannot appear inside a JSON string, so no payload can contain its own delimiter
- `api/main.py` had no CORS middleware at all. `web` calls `api` directly from the browser by design (`NEXT_PUBLIC_API_URL`, no proxy), and every one of those calls — Director's and Build's — silently failed with "Failed to fetch" the first time either was exercised against a real browser instead of a mocked `fetch`. Added a `localhost:*`-only policy, explicitly not a template for a real deployed origin
- `next.config.ts` applied the published-artifact CSP (`connect-src 'none'`, no `unsafe-eval`) to the whole `/dev/*` prefix, written when only `/dev/primitives` (zero client-side network calls) existed. A harness that calls the real API needs both; added `devToolingHeaders()` for `/dev/director` specifically
- `ai/complete.py` set no `max_tokens`. A live Build call produced a 32,000-token degenerate response over 7.4 minutes on one scene — httpx's timeout is per-read, not per-total-duration, so a slowly trickling stream never tripped it. Capped at 8000, well above every legitimate scene or outline seen so far (under 5k tokens)
