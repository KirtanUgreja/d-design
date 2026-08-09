# v2 Implementation Plan

> Thirteen phases from one art direction to three, a reskin that breaks nothing, and a pipeline that looks at what it made. Every phase is one sitting's work, has a gate in and a gate out, and cannot start before the phase it depends on is green.

**Status of the whole build lives in the table below. Status of the work *inside* a phase lives in that phase's Exit gate checklist.** Two places, no overlap — the table says which phase you are in, the checklist says how far through it you are. Do not copy status between them.

This plan implements [../spec.md](../spec.md) → Build order. It adds nothing the spec did not ask for. Where it deviates, the deviation is named in the phase file with a `ponytail:` marker and a trigger to revisit.

## Status

| # | Phase | Spec step | Status |
|---|---|---|---|
| 00 | [Foundations](00-foundations.md) | infra | not started |
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

Statuses are `not started` · `in progress` · `done` · `blocked — <why>`. Update this table when a phase changes state, and nothing else. A phase is `done` only when its Exit gate checklist is fully ticked — not when the code appears to work.

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
     ├─ 02 motion as an axis ──────────┐
     ├─ 03 AD linter ──────────┐       │
     │                         ▼       │
     └──────────────▶ 04 three art directions
                                │      │
              ┌─────────────────┼──────┴──────────┐
              ▼                 ▼                 ▼
      05 budgets in       06 version         11 range
      the pipeline          history       (motion 2-4, compare)
                                │
                                ▼
                          07 reskin ──────┬──────────┐
                                │         │          │
                                ▼         ▼          ▼
                    08 transition  09 visual   10 slides mode
                                   verification
                                                     │
                                          12 primitives (after 04)
```

**Order matters more here than it did in v1.** Steps 04–05 exist to break step 01. A format that has only ever expressed the art direction it was extracted from is not a format; it is that art direction with extra syntax. Do not build reskin before all three art directions exist — reskin against one AD is untestable, and the third AD is what tells you the format is wrong while changing it is still cheap.

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

Rules 13 and 14 are enforced by one validator with two purposes, and building it as one is what stops the security half being deferred as separate work. Rules 12 and 17 have no automated enforcement and are the two most likely to erode under deadline; phase 04 and phase 07 carry the greppable checks that approximate them.

## Where the design budget goes

v1 rationed design attention to four hot screens ([../../design/app.md](../../design/app.md)). v2's ration is different in kind: **the expensive surface is not a screen, it is a matrix.**

| Hot — craft it | Phase |
|---|---|
| The reskin transition — the screenshot people share, and from v3 the marketing hero's one interactive control | [08](08-reskin-transition.md) |
| `bold-brutalist` — the art direction that has to look deliberate rather than loud | [04](04-three-art-directions.md) |
| The overflow banner — the place the honest crack in the thesis is shown to a user | [07](07-reskin.md) |
| 18 primitives × 3 art directions = **54 surfaces** | [12](12-primitives.md) |

That last row is the single largest cost in v2, larger than the art direction system itself. It is why primitives are built last, in demand order, and why shipping v2 with fourteen of them is an acceptable outcome and not a failure.

**Everything else is furniture.** The history panel, the compare view, the AD picker's chrome, the motion picker — assembled from shadcn/ui and left alone.

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

And the honest one, which is not a checkbox: **someone who has seen the product under `cinematic-dark` looks at the same experience under `bold-brutalist` and asks what tool made it.** If the answer is visibly the same tool, the range is not real yet.
