# v1 Implementation Plan

> Twelve phases from an empty repo to a generated, edited, published experience. Every phase is one sitting's work, has a gate in and a gate out, and cannot start before the phase it depends on is green.

**Status of the whole build lives in the table below. Status of the work *inside* a phase lives in that phase's Exit gate checklist.** Two places, no overlap — the table says which phase you are in, the checklist says how far through it you are. Do not copy status between them.

This plan implements [../spec.md](../spec.md) → Build order. It adds nothing the spec did not ask for. Where it deviates, the deviation is named in the phase file with a `ponytail:` marker and a trigger to revisit.

## Status

| # | Phase | Spec step | Status |
|---|---|---|---|
| 00 | [Foundations](00-foundations.md) | — | not started |
| 01 | [Scene schema](01-scene-schema.md) | 1 | not started |
| 02 | [Art direction — design](02-art-direction-design.md) | 2 (design half) | not started |
| 03 | [Art direction — tokens](03-art-direction-tokens.md) | 2 (code half) | not started |
| 04 | [Renderer + 11 primitives](04-renderer.md) | 3 | not started |
| 05 | [Publish, present, embed](05-publish-present-embed.md) | 4 | not started |
| 06 | [Model seam + Build phase](06-model-seam-and-build.md) | 5 | not started |
| 07 | [Director phase](07-director.md) | 6 | not started |
| 08 | [Intake](08-intake.md) | 7 | not started |
| 09 | [Editor](09-editor.md) | 8 | not started |
| 10 | [Brand kit + uploads](10-brand-and-uploads.md) | 9 | not started |
| 11 | [Visuals + Slot](11-visuals-and-slot.md) | 10 | not started |

Statuses are `not started` · `in progress` · `done` · `blocked — <why>`. Update this table when a phase changes state, and nothing else. A phase is `done` only when its Exit gate checklist is fully ticked — not when the code appears to work.

## Dependency graph

```
00 foundations
 └─ 01 scene schema
     ├─ 02 AD design ──▶ 03 AD tokens ──▶ 04 renderer ──▶ 05 publish/present/embed
     │                                        │                    │
     │                                        └────────┬───────────┘
     │                                                 ▼
     └──────────────────────────────────────▶ 06 model seam + build
                                                       │
                                          ┌────────────┼────────────┐
                                          ▼            ▼            ▼
                                     07 director   08 intake    09 editor
                                                                    │
                                                       ┌────────────┴────────┐
                                                       ▼                     ▼
                                              10 brand + uploads     11 visuals + Slot
```

**Phases 00–05 involve no AI at all.** That is the point, and it is the spec's instruction rather than this plan's preference: hand-write a scene tree, render it, look at it. It is the cheapest possible test of Risk 1, and Risk 1 is the only risk that can kill the product outright.

## The one hard gate

> **Do not start phase 06 until phase 04 looks genuinely good.**

Not "renders without errors." Not "all eleven primitives appear." Good. If the renderer under `cinematic-dark` does not produce something you would be pleased to have made, the pipeline that fills it is worthless and the editor that adjusts it is worthless. [../spec.md](../spec.md), Risk 1.

Phase 02 exists so this judgment has something to be made against — a hand-designed comp, made before a single token was written, is the reference the renderer is compared to. A renderer judged against nothing is always "fine."

## How to read a phase file

Every phase file has the same four sections, in this order:

| Section | |
|---|---|
| **Search** | What to read before writing, what to grep for in the code that already exists, and what to verify externally. The grep list is not ceremony — duplication is the measured failure mode of AI-written code ([../../coderules/ai-authorship.md](../../coderules/ai-authorship.md)), and naming the existing thing before writing is the defense |
| **Make** | The files, in build order, with the decisions already taken. Exact paths, so nothing lands in the wrong feature |
| **Verify** | Three tiers: the gate (typecheck, lint, format), the phase's own tests, and the rows of [../../security/testing.md](../../security/testing.md) that become live in this phase. Plus the human checks a machine cannot do |
| **Skipped** | What was deliberately not built, and the trigger that would build it. Every entry here should also exist as a `ponytail:` comment in the code |

Then an **Exit gate** checklist. That checklist is the phase's definition of done.

## Rules that apply to every phase

These are not restated per phase. They are the eleven non-negotiables from [../../coderules/README.md](../../coderules/README.md), and a violation is a defect regardless of which phase produced it:

1. Strict TS, no `any`, no `!`
2. One Zod parse per external input, at entry — model output and tool arguments included
3. Expected failures return `Result`; only bugs throw
4. Cross-feature imports go through `index.ts`
5. No dependency without a ledger line in [../../coderules/dependencies.md](../../coderules/dependencies.md)
6. `renderer/` is pure — no `mode`, no `process.env`, no `typeof window`
7. AI output carries no presentational values
8. Drizzle only in `*.data.ts`, and those start with `import 'server-only'`
9. Every tenant-scoped query goes through `asUser()`
10. Anything that grants, fails closed
11. The gate is green or the commit does not land

Rules 9 and 10 guard threats that do not exist in single-user v1. They are built anyway, in phase 00, because their entire value is that the habit is greppable from the first commit — retrofitting rule 9 across forty call sites in v3 is the documented failure, not building it in v1.

## Where the design budget goes

v1 builds the only UI that exists, and [../../design/app.md](../../design/app.md) rations the attention it gets. **Four screens are hot; the rest is furniture**, and furniture that is quiet is good furniture. This is the cold-90% rule from [../../coderules/performance.md](../../coderules/performance.md) applied to design time rather than to CPU time.

| Hot — craft it | Phase |
|---|---|
| The generation watch — 40 seconds, and the highest-leverage motion design in the product | [06](06-model-seam-and-build.md) |
| The outline gate — hot for *trust* rather than for delight | [07](07-director.md) |
| Intake, the first prompt | [08](08-intake.md) |
| The publish reveal, and the editor's answer to the missing colour picker | [05](05-publish-present-embed.md), [09](09-editor.md) |

Everything else — settings, the asset list, the brand-kit form, the property panel's chrome — is assembled from shadcn/ui and left alone. A week spent on a settings page while the generation watch is a spinner is the budget spent backwards.

**Settle the product's name before phase 09.** Nothing in the build blocks on it, which is exactly why it slips; the editor is the first place user-facing strings accumulate, and renaming across a UI afterwards is an audit rather than an edit ([../../design/brand.md](../../design/brand.md)).

## What v1 does not build, and why the plan says so

The spec's *Not in v1* list stands unchanged. Two things this plan removes that a reader might expect from the docs:

**Document and URL import.** [../ai-pipeline.md](../ai-pipeline.md) specifies Intake's import path running extraction in the isolated fetch worker. The fetch worker is v3 infrastructure ([../../techstack/infrastructure.md](../../techstack/infrastructure.md)), and running a PDF parser in the app is the one placement [../../coderules/dependencies.md](../../coderules/dependencies.md) says should feel wrong. **v1 Intake is prompt and AI-led Q&A only.** The `Brief` shape is identical either way, so import is purely additive when the worker exists — see [08-intake.md](08-intake.md).

That deletion also removes v1's only untrusted-input path, which is why the injection corpus in phase 06 runs against pasted text rather than against documents.

**`@d-design/schema` as a published package.** [../../coderules/structure.md](../../coderules/structure.md) publishes the schema so the fetch worker can consume it. With no fetch worker there is no consumer, and a package with no consumers is a release process with no purpose. The schema lives at `src/schema/` with the folder layout a package would have, so publishing it later is a `package.json` and a Changeset — see [01-scene-schema.md](01-scene-schema.md).

## v1 is done when

The end-to-end run from [../spec.md](../spec.md) → Verification passes in one sitting, unassisted:

- [ ] Prompt or Q&A produces a `Brief`
- [ ] Director produces an `Outline`, and it is editable before anything is built
- [ ] Build streams 8 scenes, every one Zod-valid after at most one repair
- [ ] Edit a headline through the property panel, and again through an element-scoped prompt — both produce the same patch shape
- [ ] Publish, open the URL in a private window
- [ ] Fullscreen, navigate with arrow keys
- [ ] Embed in a blank HTML page and it renders
- [ ] `prefers-reduced-motion: reduce` collapses all motion
- [ ] Every `Image` has non-empty `alt`
- [ ] `dir="rtl"` on the root mirrors the layout with no stylesheet change
- [ ] `generations` contains no prompt, no output, and no brief content
- [ ] The gate is green and CI is green

And the honest one, which is not a checkbox: **you would show it to someone.**
