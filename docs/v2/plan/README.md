# v2 Implementation Plan

> Eighteen phases from one art direction to three, a reskin that breaks nothing, a pipeline that looks at what it made, and output that survives being looked at. Every phase is one sitting's work, has a gate in and a gate out, and cannot start before the phase it depends on is green.

**Status of the whole build lives in the table below. Status of the work *inside* a phase lives in that phase's Exit gate checklist.** Two places, no overlap — the table says which phase you are in, the checklist says how far through it you are. Do not copy status between them.

This plan implements [../spec.md](../spec.md) → Build order. It adds nothing the spec did not ask for. Where it deviates, the deviation is named in the phase file with a `ponytail:` marker and a trigger to revisit.

## Status

| # | Phase | Spec step | Status |
|---|---|---|---|
| 00 | [Foundations](00-foundations.md) | infra | **in progress** — migrations done (0008–0010); `render` service not built |
| 01 | [AD format v2](01-ad-format.md) | 1 | not started |
| 02 | [Motion as an axis](02-motion-axis.md) | 2 | not started |
| 03 | [The AD linter](03-ad-linter.md) | 3 | not started |
| 04 | [Three art directions](04-three-art-directions.md) | 4, 5 | not started |
| 05 | [Budgets in the pipeline](05-budgets-in-the-pipeline.md) | pipeline delta | not started |
| 06 | [Version history](06-version-history.md) | 6 | not started |
| 07 | [Reskin](07-reskin.md) | 7 | not started |
| 08 | [The reskin transition](08-reskin-transition.md) | 8 | not started |
| 09 | [Visual verification](09-visual-verification.md) | 9 | not started |
| 10 | [Slides mode](10-slides-mode.md) | 12 | not started |
| 11 | [Range: motion and compare](11-range.md) | 10, 11 | not started |
| 12 | [Seven primitives](12-primitives.md) | 13 | not started |
| 13 | [The scene as a stage](13-scene-fit.md) | delta | **in progress** — fit shell done; viewport overflow deferred to after [00](00-foundations.md) |
| 14 | [Texture without gradient](14-texture-without-gradient.md) | delta | **done** |
| 15 | [Images that exist](15-images.md) | delta | **done** |
| 16 | [Charts](16-charts.md) | delta | not started |
| 17 | [Composition](17-composition.md) | delta | not started |

Statuses are `not started` · `in progress` · `done` · `blocked — <why>`. Update this table when a phase changes state, and nothing else. A phase is `done` only when its Exit gate checklist is fully ticked — not when the code appears to work.

## The five phases added after the plan was written, and why they are numbered last

Phases 13–17 were added on 2026-08-09, after the first generated experiences were looked at rather than reasoned about. They are numbered last because **a phase number is a filename, not a position** — renumbering thirteen files to insert five would break every cross-reference in the corpus to buy nothing. Several of them build *early*; the dependency graph below is the authority on order and the numbers are not.

They exist because four defects were visible in the output and none of them was in this plan:

| What was wrong | Phase | Why the original plan could not have caught it |
|---|---|---|
| Scenes are content-height, so two share the viewport and neither is composed | [13](13-scene-fit.md) | Nothing in v1 or v2 ever said what a scene's *frame* is. The renderer tests assert structure, and structure was correct |
| The renderer is built out of gradients — a coloured bloom behind every hero, four of five visual generators | [14](14-texture-without-gradient.md) | [../../design/principles.md](../../design/principles.md) principle 5 bans exactly this, and it was filed under `docs/design/`, which everyone read as being about *our chrome*. The artifact was exempt by filing rather than by decision |
| Every `Image` block renders a grey rectangle | [15](15-images.md) | It was recorded honestly, twice, as a v1 deferral — and then not picked up by any v2 phase. A gap two docs agree on can still belong to nobody |
| A page of numbers has no way to show a trend, and generated pages are eight centred scenes in a row | [16](16-charts.md), [17](17-composition.md) | Charts were refused on reasoning that was about a charting *tool*. Sameness is invisible to a schema and was invisible to a plan written before there was output |

**The pattern is worth naming, because it will recur.** Every one of these is a *presentational* property, and this plan's entire quality apparatus — the schema, the linter, the gate, the invariants script — is built to verify **structure**. All four defects passed every check the product had. The visual critic in [09](09-visual-verification.md) is the only mechanism in v2 aimed at this class, which is an argument for it landing earlier than it does, and its questions should be extended by what these phases fix.

## What v1 already delivered, and what that changes

**v1 shipped art direction #2.** [../../v1/spec.md](../../v1/spec.md) Risk 4 said the layer was unproven until there were two, so `editorial-light` was built as the falsification test the day v1's acceptance run passed ([../../v1/art-direction.md](../../v1/art-direction.md) → "The result"). That was the right call and it moves this plan's ground:

| Spec step | What already exists | What this plan still owes it |
|---|---|---|
| 1 — AD format v2 | Types split from values; a `FontFamilyId` registry keyed by family; `ArtDirectionId` is a schema `Literal` | `budgets`, `version`, `brandMapping`, DTCG primitives, and the `art_directions` table. **The format is still v1's** |
| 2 — motion as its own axis | Two `MotionVocabulary` objects, and `resolveArtDirection` pairs one to each AD | The pairing is a code table, not a **selectable axis on the experience**. That is the whole of phase 02 |
| 4 — `editorial-light` | Hand-authored, linted by eye, shipped | Migrating it into the v2 format, and re-authoring anything the linter rejects |

**Two findings from that exercise bind this plan.** They are not restated in every phase file:

1. **A token read is the exercise working; a branch is the abstraction failing.** v1's original test — "if it requires *any* renderer change, the abstraction is wrong" — was too blunt. Two renderer files changed for AD #2 and both were a hardcoded value becoming a token, which is what the layer's own rules instruct. Phase 04's exit gate uses the sharpened test.
2. **The values a system holds globally are the ones it holds because it only ever had one instance.** Four of the seven things AD #2 cost were exactly that shape. Expect `bold-brutalist` to find more, and treat finding them as the phase succeeding.

## Dependency graph

```
00 foundations (render service · published schema · migrations)
 └─ 01 AD format v2
     ├─ 02 motion as an axis ─────────────────────┐
     ├─ 13 scene fit ───────────────┐             │
     ├─ 14 texture (no gradient) ───┤             │
     │        └─ 15 images ─────────┤             │
     ├─ 03 AD linter ───────────────┤             │
     │       (+ 14's neon bounds)   ▼             │
     └──────────────────▶ 04 three art directions │
                                │  │  │           │
       ┌────────────────────────┘  │  └───────────┼────────┐
       ▼                           ▼              ▼        ▼
 05 budgets in            16 charts        06 version   11 range
 the pipeline           17 composition       history  (motion 2-4,
                     (also needs 13,14,15)      │        compare)
                                │               ▼
                                │         07 reskin ──┬─────────┐
                                │               │     │         │
                                ▼               ▼     ▼         ▼
                          09 visual   08 transition  10 slides mode
                          verification
                                            12 primitives (after 04)
```

**Order matters more here than it did in v1.** Steps 04–05 exist to break step 01. A format that has only ever expressed the art direction it was extracted from is not a format; it is that art direction with extra syntax. Do not build reskin before all three art directions exist — reskin against one AD is untestable, and the third AD is what tells you the format is wrong while changing it is still cheap.

**Three of the new phases land before 04, and that placement is the whole point of adding them where they are.** 13, 14 and 15 each add tokens — `fit`, six texture kinds, `ImageTreatment` — and an art direction authored before those tokens exist is an art direction that has to be re-authored after them. Authoring `bold-brutalist` against a format that has no image treatment means discovering at phase 15 that it needed one, which is precisely the "expect the format to be wrong" cost [04](04-three-art-directions.md) is trying to pay once instead of three times. 14 also lands before 03, because the linter's neon bounds are that phase's output.

The two that land after 04 do so for the opposite reason: [16](16-charts.md) and [17](17-composition.md) are both **three-art-direction problems**. A chart authored against one AD is a chart with that AD's opinions baked in, and composition tokens whose values were only ever chosen for `cinematic-dark` are the same trap in a different group. Building them after three ADs exist is what makes them tokens rather than defaults.

**Recommended build order**, which is the graph flattened:

```
13a · 00 · 01 · 13b · 14 · 15 · 02 · 03 · 04 · 17 · 05 · 16 · 06 · 07 · 08 · 09 · 10 · 11 · 12
```

**[13](13-scene-fit.md) splits, and its first half went first.** The graph above shows 13 hanging off 01, which was drawn reflexively and is not true of the code: the fit shell is three `Rhythm` tokens, four CSS variables and two component edits, all in files that exist today. Only section 9 of that phase — viewport overflow reporting — needs a headless layout and therefore [00](00-foundations.md)'s `render` service. `13a` is the shell and is **done**; `13b` is the overflow half and waits.

It was built out of order on purpose. The defect it fixes is the one visible in the generated output, and 00 and 01 deliver nothing anyone can look at. Nothing is built twice — 01's job is migrating v1's format into v2's, and three more tokens is that job. **Check the other arrows in this graph the same way before treating one as a cost**; at least one more of them is a reflex rather than a dependency.

[17](17-composition.md) sits immediately after 04 because it is the phase that decides whether the three art directions look like three designs or three colour schemes, and that is a judgement best made while all three are still fresh and cheap to change.

## The one hard gate

> **Do not start phase 07 until `bold-brutalist` renders every primitive without a renderer change.**

Not "renders without crashing". Without a **branch** — no `mode`, no `if (artDirection.id === …)`, no second layout path. A token read is fine and expected; that is the distinction v1's AD #2 exercise established and phase 04 is where it gets its real test, because `bold-brutalist` is the art direction designed to break things.

If it needs a branch, the format is wrong. Stop and fix the format. That is cheaper at phase 04 than at any later point in the product's life, and it is the entire reason three art directions are hand-authored before a single user-authored one exists.

## How to read a phase file

Every phase file has the same four sections, in this order — the same shape as [../../v1/plan/README.md](../../v1/plan/README.md), because the discipline does not change when the release does.

| Section | |
|---|---|
| **Search** | What to read before writing, what to grep for in the code that already exists, and what to verify externally. The grep list is not ceremony — duplication is the measured failure mode of AI-written code ([../../coderules/ai-authorship.md](../../coderules/ai-authorship.md)), and naming the existing thing before writing is the defense |
| **Make** | The files, in build order, with the decisions already taken. Exact paths, so nothing lands in the wrong feature |
| **Verify** | Three tiers: the gate (typecheck, lint, format, schema regeneration), the phase's own tests, and the rows of [../../security/testing.md](../../security/testing.md) that become live in this phase. Plus the human checks a machine cannot do |
| **Skipped** | What was deliberately not built, and the trigger that would build it. Every entry here should also exist as a `ponytail:` comment in the code |

Then an **Exit gate** checklist. That checklist is the phase's definition of done.

## Rules that apply to every phase

The eleven non-negotiables from [../../coderules/README.md](../../coderules/README.md) still apply unchanged, and a violation is a defect regardless of which phase produced it. **v2 adds six**, all of which exist because this is the release where a token value stops being something you wrote.

12. **Art directions are tokens-only.** No AD-specific layout, no AD-specific component, no AD-specific branch in the renderer. The instant an AD can add a layout, "any AD applies to any experience" becomes "works unless the target AD lacks the source's layout", and reskin dies as a promise ([../spec.md](../spec.md) → Locked decisions)
13. **Every token value is parsed by type and re-serialized. Nothing is passed through as a string**, and font families are ids into a registry ([../../security/content-and-web.md](../../security/content-and-web.md) → "CSS injection via art-direction tokens")
14. **Both contrast standards are hard failures.** WCAG 2.2 AA is the legal floor; APCA is the perceptual gate. An AD failing either cannot be saved ([../art-direction-system.md](../art-direction-system.md) → "The AD linter")
15. **A published page never restyles itself.** The AD reference is `{ id, version }` and publishing pins it. Upgrading is opt-in, with a preview
16. **The critic never acts.** The visual loop is a `for` with a literal limit of 1, its output stays inside a fixed schema, and its verdict triggers no tool call and no write ([../../techstack/ai-stack.md](../../techstack/ai-stack.md))
17. **Nothing rewrites approved copy without being asked.** Overflow is flagged, visibly and deliberately annoyingly; shortening is one click and shows the proposed text first ([../transformations.md](../transformations.md))
18. **No gradient, anywhere in the artifact.** No `linear-`, `radial-`, `conic-` or `repeating-*-gradient`, in the renderer, in a token value, or in a generated visual. Colour changes by dot, line, dither or hard edge. [../../design/principles.md](../../design/principles.md) principle 5 governs the artifact and not only our chrome, and [14](14-texture-without-gradient.md) is where that stops being an aspiration — `scripts/checks/invariants.sh` check 8
19. **No neon, no bloom, no glow.** No `blur()`, no `backdrop-filter` as bloom, no chromatic `box-shadow` or `text-shadow` at any radius, no luminous edge. A hard offset shadow with zero blur is a print device and is allowed; the banned property is the blur. Saturation is bounded by value in the linter rather than by taste — invariants check 9
20. **A scene owns its frame.** Whether a scene fills the viewport is the art direction's lookup from the layout the AI wrote, never a field the AI sets and never a renderer constant ([13](13-scene-fit.md))
21. **A number on a published page traces to something the user supplied.** A `Chart` whose points do not trace to a proof point in the approved Brief is rejected before storage, and `source` is a required field, not an optional one ([16](16-charts.md))

Rules 13 and 14 are enforced by one validator with two purposes, and building it as one is what stops the security half being deferred as separate work. Rules 18 and 19 are greppable by construction — that is why they are written as property bans rather than as taste guidance, and each is verified by breaking it and watching the gate go red. Rules 12, 17 and 20 have no automated enforcement and are the three most likely to erode under deadline; phases 04, 07 and 13 carry the greppable checks that approximate them.

## Where the design budget goes

v1 rationed design attention to four hot screens ([../../design/app.md](../../design/app.md)). v2's ration is different in kind: **the expensive surface is not a screen, it is a matrix.**

| Hot — craft it | Phase |
|---|---|
| The reskin transition — the screenshot people share, and from v3 the marketing hero's one interactive control | [08](08-reskin-transition.md) |
| `bold-brutalist` — the art direction that has to look deliberate rather than loud | [04](04-three-art-directions.md) |
| The overflow banner — the place the honest crack in the thesis is shown to a user | [07](07-reskin.md) |
| 18 primitives × 3 art directions = **54 surfaces** | [12](12-primitives.md) |
| The six texture kinds — the replacement vocabulary has to be *better* than the gradients, not merely compliant | [14](14-texture-without-gradient.md) |
| Image treatment — one photograph reading three ways is the best demonstration of the whole thesis | [15](15-images.md) |
| 5 chart marks × 3 art directions = 15 surfaces | [16](16-charts.md) |
| The composition tokens, and Intake + the outline gate, deferred from v1 | [17](17-composition.md) |

That 54-surface row is the single largest cost in v2, larger than the art direction system itself. It is why primitives are built last, in demand order, and why shipping v2 with fourteen of them is an acceptable outcome and not a failure.

**The four rows below it are new, and they change where the budget actually goes.** v1's ration went to four hot *screens*; the first draft of this plan said the expensive surface was a matrix. Both were right about the app and wrong about the artifact: the most expensive surface in v2 is **the generated page itself**, and it is the only one nobody had costed. Every row added here is artifact craft, and none of it is furniture.

**Everything else still is.** The history panel, the compare view, the AD picker's chrome, the motion picker — assembled from shadcn/ui and left alone.

## What v2 does not build, and why the plan says so

The spec's *bets* table stands. Two things this plan removes that a reader might expect:

**AI-derived art directions.** [../art-direction-system.md](../art-direction-system.md) records the stance — extract abstract qualities, never fonts, colours, or literal layouts — and that stance is decided, but the build is v3. It needs the token schema battle-tested by hand and by users first, and v2 is what does the battle-testing. The four user control axes in phase 04's Skipped table are the same four the AI will fill in later, which is why they are designed now and not built now.

**The marketplace.** v3+, gated on real users. A designer channel with no designers is an empty room. What v2 owes it is a portable format, which is the whole reason the primitive token layer is stored as DTCG in phase 01.

## v2 is done when

Everything in [../spec.md](../spec.md) → Verification passes, in one sitting, unassisted:

- [ ] All 3 art directions express fully in the format with **no renderer branch**
- [ ] The linter rejects a deliberately broken AD on every rule — 2:1 contrast, non-monotonic scale, 4s durations
- [ ] The linter rejects a token whose colour is `red; } body { background: url(//evil` and whose font family is a free string — **rejected, not sanitized**
- [ ] An AD that passes WCAG 2.2 AA at 4.6:1 but scores `Lc 55` on dark is **rejected**
- [ ] The visual critic flags a 78-character headline under `bold-brutalist` and text over a busy image with no veil — both schema-valid, both visually broken
- [ ] Reskin a 12-scene experience: no duplicate `view-transition-name` in the document, and off-screen blocks carry none
- [ ] The reskin matrix — 3 ADs × 4 motion vocabularies × 2 modes × 5 golden experiences — renders valid, no crashes, overflow correctly reported
- [ ] Publish under AD v1, bump the AD to v2, and the published page is byte-identical
- [ ] Reskin, restore, and the tree is identical to the pre-reskin snapshot
- [ ] Content that fits a scroll scene and not a slide is flagged, never silently clipped
- [ ] Every primitive shipped renders under all 3 art directions
- [ ] `prefers-reduced-motion: reduce` collapses motion under all 4 vocabularies, in both modes
- [ ] The gate is green and CI is green

And the boxes the five added phases put on this list, which are about the output rather than the system:

- [ ] At most one scene boundary is visible in a 100svh frame, across all 5 golden experiences and all 3 art directions — and a scene taller than the frame is still fully readable
- [ ] Zero gradient functions and zero blurs under `renderer/` and `art-direction/`, enforced by grep and verified by breaking each check
- [ ] An uploaded photograph renders, and the **same** photograph under 3 art directions produces 3 visibly different images with no re-encode and no second asset row
- [ ] A generated image goes through the single seam, is capped, is marked `source: 'generated'`, and its prompt carries no key messages and no token values
- [ ] Five chart marks render under 3 art directions, distinguishable in greyscale, with a zero baseline on bars and a required `source` — and a chart of invented numbers is rejected in the build path
- [ ] Ten generated experiences: none has three consecutive identical layouts, all meet the visual ratio floor, none opens and closes on the same layout, every scene has exactly one anchor

And the honest one, which is not a checkbox: **someone who has seen the product under `cinematic-dark` looks at the same experience under `bold-brutalist` and asks what tool made it.** If the answer is visibly the same tool, the range is not real yet.

There is now a second honest one, and it comes first: **generate a page from a cold prompt, put it full-screen next to a page from a design studio, and ask someone which is which.** v2's original list could go entirely green while the answer stayed obvious, because every box on it verifies the system and none verifies the artifact. That is the gap phases 13–17 exist to close, and this is the only question that tells you whether they did.
