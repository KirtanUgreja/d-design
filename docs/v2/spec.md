# v2 Spec — Creative Range

## Theme

v1 proves an experience can be generated, edited, and published. **v2 proves it can be anything.**

Same content, same scene tree, radically different experiences — switched with one click. That is the feature no template tool can copy, because they never separated content from styling in the first place.

## The honest caveat

**v2 is being specified before v1 has a single user.** Every pre-launch v2 is partly wrong, because the thing users complain about is never the thing you predicted.

So this doc separates two kinds of statement.

### Commitments — true regardless of what users say

| | Why it survives feedback |
|---|---|
| AD format v2: budgets, versioning, brand mapping | v1's format cannot express a second art direction. This is a defect, not a preference |
| Motion as an independent axis | 3 ADs × 4 motion vocabularies = 12 combinations for a fraction of the work |
| AD linter with hard failures | User-authored ADs can produce unreadable pages carrying your name — and, once token values are user-controlled, CSS injection on them |
| 3 hand-authored art directions | The only way to discover what the token schema is missing |
| Version history | One-click reskin without undo is a feature that eats people's work |
| One-click reskin | The architecture already implies it; not shipping it wastes v1 entirely |

### Bets — may be wrong, revisit after real usage

| | What would disprove it |
|---|---|
| 7 new primitives, and *these* 7 | Users ask for three others and ignore five of these |
| Slides mode demand | Nobody presents live; everyone shares links |
| Users want AD *controls* rather than curated choices | Marketers pick from a list and never touch a slider |
| Compare view | Users decide from thumbnails and never open it |

## Locked decisions

| Axis | Decision | Why |
|---|---|---|
| Theme | Creative range explodes | The abstraction is unproven with one AD (v1 Risk 4) |
| Headline feature | One-click reskin | Makes the abstraction visible to users, not just architects |
| AD scope | **Tokens only** | Any AD must work with any experience, or reskin can't be guaranteed |
| AD authoring | 3 hand-authored, then user controls | Hand-authoring is the prerequisite, not a competing option |
| AI-derived AD | **v3** | Needs the token schema battle-tested by hand and by users first |
| Marketplace | **v3+**, gated on real users | A designer channel with no designers is an empty room |
| Motion | Independent axis from visual AD | Cheapest range multiplier available |
| Content fit | Per-AD character budgets, flagged overflow | Never silently rewrite approved marketing copy |
| AD versioning | Pinned at publish, opt-in upgrade | A live launch page must not restyle itself overnight |
| History | Auto-snapshot at milestones + named saves | Scene trees are small JSON; storing 50 costs nothing |
| Slides mode | One scene = one slide, motion retimed | No content changes, no second authoring pass |
| Delight budget | The reskin transition | It's the screenshot people share |
| Pricing | Still deferred — v3 | v2 is about being loved, not monetized |

## What v2 changes from v1

Per the versioning convention, v1 docs stay as the record of what was believed. These are the deltas.

| v1 said | v2 says | Why |
|---|---|---|
| Character caps are universal constants | Caps are **per art direction** | 58 chars is elegant in editorial-light, catastrophic in brutalist |
| `artDirection: 'cinematic-dark'` — one value | AD reference is `{ id, version }` | Published experiences must not mutate when tokens improve |
| Motion vocabulary belongs to the art direction | Motion is a **separate selectable axis** | Decoupling multiplies range for near-zero cost |
| 11 primitives | 18 primitives | Structural range to match stylistic range |
| No version history | Auto-snapshots + named saves | Reskin makes it a hard dependency |
| `mode: 'scroll' \| 'slides'`, scroll rendered only | Both render | Makes the presentation framing finally honest |
| Zod validation is the whole quality gate | Zod **plus a visual critic** | Zod proves valid, never good. Layout breakage across ADs is invisible to a validator |
| AD token values are hand-authored by you | Partly **user-controlled**, and validated by grammar before becoming CSS | The first release where a token value is untrusted input |

**Migration:** existing v1 experiences get `artDirection: { id: 'cinematic-dark', version: 1 }` and the v1 caps become that AD's budgets. No content changes. The `scenes` jsonb shape is otherwise unchanged.

## Platform reality (researched August 2026)

Four capabilities matured between this design being sketched and being built. Each removes work rather than adding it.

| Capability | Status | What it changes |
|---|---|---|
| **View Transitions (same-document)** | **Baseline** since Oct 2025 · React 19.2 `<ViewTransition>` · Next.js 16 | The reskin transition is a state update, not a FLIP implementation. **Delete that code before writing it** |
| **`color-mix()` / OKLCH / relative color** | `color-mix()` Baseline Widely Available (~89%) · OKLCH ~87% · relative syntax shipped everywhere | `brandMapping` derives the accent family in CSS at runtime. No build step, no JS color pass, and reskin gets cheaper |
| **DTCG token format** | First stable version **2025.10** (Oct 2025) · Figma, Sketch, Framer, Style Dictionary, Tokens Studio | The AD primitive layer should be a `.tokens.json` file with semantics in `$extensions` — free interchange for v4's marketplace |
| **APCA** | WCAG 3.0 draft algorithm; in Chrome DevTools | The linter needs it. **WCAG 2.x cannot evaluate dark mode**, and the flagship AD is dark |

The APCA one is the only entry on this list that *adds* a requirement rather than removing work. It also happens to be the one most likely to change what `cinematic-dark` actually looks like.

## Architecture delta

```
                        ┌── art direction (tokens) ──┐
scene tree ─────────────┤                            ├──▶ SceneRenderer
(unchanged from v1)     ├── motion vocabulary ───────┤
                        └── playback mode ───────────┘
                              scroll | slides
```

The scene tree does not change. Three independent axes now sit between it and the renderer, and any combination is valid. That property is what makes reskin safe, and it survives only if **art directions stay tokens-only** — the moment an AD can add a layout or a component, "any AD works with any experience" becomes a lie.

Docs: [art-direction-system.md](art-direction-system.md) · [transformations.md](transformations.md) · [primitives.md](primitives.md)

## Pipeline delta

The four phases from [v1/ai-pipeline.md](../v1/ai-pipeline.md) are unchanged in shape. Three things change in what they receive.

**Art direction is chosen before Build, not after.** Budgets are per-AD, so the Build phase cannot write copy until it knows which AD it is writing for. The AD picker moves into the outline-approval gate, defaulting to `cinematic-dark`.

**Build receives the AD's budgets, not universal caps.** The character limits injected into the build prompt and the Zod schema are read from `artDirection.budgets`. Generating for `bold-brutalist` means a 34-character headline limit at generation time — which produces genuinely different copy, not the same copy truncated.

**Build receives AD character as context.** Dense ADs want fewer blocks per scene. `bold-brutalist` with six blocks in a scene is unreadable at any budget. Each AD declares a `maxBlocksPerScene` hint the Director uses when assigning layouts.

Edit-phase patches are re-validated against the current AD's budgets. Editing a headline into overflow flags it exactly as reskin does — one mechanism, three entry points.

### The visual verification loop arrives here

**v2 is the release where the pipeline starts looking at what it made** ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)). It lands in v2 and not v1 for a reason that is specific rather than schedule-driven: the defect it catches is *layout breaking across art directions*, and that defect does not exist until there is more than one art direction.

```
Build ──▶ Scene JSON ──▶ Zod ──▶ render offscreen ──▶ screenshot ──▶ vision critic
                          │                                              │
                    (invalid: repair)                          accept · revise once
```

Zod proves a tree is **valid**. Nothing in v1 proves it is **good** — that headlines are not colliding, that a `split-left` with 200 characters of body is not overflowing its region, that a stat is legible against what sits behind it, that scene 4 does not look identical to scene 3. Those are visual properties and they are invisible to a validator by definition.

Three things about it that shape v2 specifically:

**Render under the real art direction, at full fidelity.** The instinct is to check layout on a cheap wireframe. That instinct is documented to be wrong — improving render fidelity *without* fixing layout intent makes the critic's evaluation worse, because better rendering exposes defects flat rendering concealed. A flat render hides the overlap `bold-brutalist`'s 12vw hero creates. You are not checking an abstract layout; you are checking the page a viewer sees.

**Which makes it per art direction — and therefore the natural gate for reskin.** The moment content moves to a different AD with different budgets is exactly when layout breaks, and it is the moment a character-count check cannot see the breakage. This is the loop's highest-value application in v2 and the reason it belongs to this release.

**The critic is asked narrow questions.** "Is any text clipped or overlapping?" "Is every text element legible against what is behind it?" "Does this scene look meaningfully different from the previous one?" Not "is this good" — a vision model asked that returns flattery. **Beauty is not among the questions**; the critic catches broken, not boring, exactly as the AD linter enforces readability and has no opinion on taste.

One revision, then accept. An unbounded critic loop is a token furnace that converges on nothing, and it is the precise autonomy that would turn this pipeline into an agent ([../techstack/ai-stack.md](../techstack/ai-stack.md)). Cost roughly doubles, from ~$0.20 to ~$0.40 per experience — which at these numbers is not a cost decision.

## Editor delta

What v2 adds to the v1 editor, consolidated:

| Surface | Behavior |
|---|---|
| AD picker | In the outline gate and in the editor toolbar. Switching in the editor runs the full reskin flow |
| Motion picker | Separate control. AD's `defaultMotion` preselected, other 3 available |
| Mode toggle | Scroll ↔ slides. Runs the same overflow check |
| Overflow banner | Appears after any transformation. Per-block review + shorten-with-AI |
| History panel | Snapshot list with trigger labels, named saves, restore |
| AD version prompt | "This art direction has been updated" — side-by-side preview, opt in |
| Compare view | 3 ADs side by side, scroll-synced. *Bet — first thing to cut* |
| Asset source badge | Carried from v1: `generated` vs `upload` stays visible |

## Persistence delta

```
art_directions      id, version, tokens (jsonb), budgets (jsonb),
                    brand_mapping (jsonb), default_motion, author, created_at
motion_vocabularies id, version, tokens (jsonb)
snapshots           id, experience_id, scenes (jsonb), art_direction,
                    motion_vocabulary, label, trigger, created_at
experiences         + motion_vocabulary, + art_direction is now {id, version}
```

`art_directions` holds hand-authored and user-authored ADs in the same table. If the format can't express both, it's the wrong format — and finding that out early is the point.

## Build order

**Order matters more than usual here.** Steps 4–5 exist to break step 1.

1. AD format v2 — budgets, versioning, brand mapping. Migrate `cinematic-dark` into it
2. Extract motion into a separate `cinematic-slow` vocabulary; renderer reads two sources
3. AD linter — contrast, scale monotonicity, motion bounds, **and token grammar validation** ([art-direction-system.md](art-direction-system.md))
4. **Hand-author `editorial-light`**
5. **Hand-author `bold-brutalist`** — this is where missing tokens surface
6. Version history / snapshots
7. Reskin + overflow report + shorten-with-AI
8. Reskin transition — wrap the state update in `<ViewTransition>`, scope `view-transition-name` to the viewport. *Much cheaper than planned; see Platform reality*
9. **Visual verification loop** — render, screenshot, critic, one revision. Wire it to reskin first, where it earns its cost immediately
10. Compare view
11. Remaining motion vocabularies: `editorial-restrained`, `mechanical-snap`, `physics-playful`
12. Slides mode — reuses the overflow mechanism from step 7
13. The 7 primitives, in order of real demand

Do not build reskin (7) before both new ADs exist (4–5). Reskin against one AD is untestable, and the second and third ADs are what tell you the format is wrong while it's still cheap to change.

Step 9 sits after reskin deliberately. The loop needs something to look at and a reason to look — before three ADs exist, it is an expensive way to confirm that a page you already stared at is fine.

**Infrastructure in v2: unchanged from v1.** Docker Compose and a dev server ([../techstack/infrastructure.md](../techstack/infrastructure.md)). Three art directions, reskin, and the visual loop are pure application work — the loop needs a headless browser locally, not a deployed one. AWS lands with v3, which is the release that has users.

## Verification

| What | How |
|---|---|
| **AD format completeness** | All 3 ADs express fully in the format with zero renderer changes. **If any AD needs a renderer change, the abstraction is wrong — stop and fix it.** |
| **Linter** | Feed it a deliberately broken AD (2:1 contrast, non-monotonic scale, 4s durations). Every rule must fail it. |
| **Token grammar** | Feed it an AD whose color token is `red; } body { background: url(//evil` and whose font family is a free string. Both **rejected as hard failures**, not sanitized — [../security/content-and-web.md](../security/content-and-web.md) |
| **Visual critic catches what Zod cannot** | Hand-build a scene that is Zod-valid and visually broken — a 78-character headline under `bold-brutalist`, text over a busy image with no veil. The critic must flag both. A critic that passes them is miscalibrated and worse than none |
| **Dual contrast** | An AD that passes WCAG 2.2 AA at 4.6:1 but scores `Lc 55` on dark must be **rejected**. If it passes, the APCA gate isn't wired — and that combination is exactly what muddy dark themes look like |
| **View-transition names** | Reskin a 12-scene experience: assert no duplicate `view-transition-name` in the document, and that off-screen blocks carry none |
| **Reskin matrix** | 3 ADs × 4 motion vocabularies × 2 modes = 24 combinations against 5 golden experiences. All must render valid, no crashes, overflow correctly reported. |
| **Version pinning** | Publish under AD v1, bump AD to v2, confirm the published page is byte-identical. |
| **History** | Reskin, restore, assert the tree is identical to the pre-reskin snapshot. |
| **Slides overflow** | Content that fits a scroll scene and not a slide is flagged, never silently clipped. |
| **Primitives** | All 18 rendered under all 3 ADs. Visual judgment — 54 surfaces, and this is the real cost of v2. |

## Risks

**1. Three ADs may prove the token schema wrong.** That is the *purpose* of steps 4–5, not a failure of them. Budget for a format refactor between AD #2 and AD #3, and treat needing one as the process working.

**2. ~~The reskin transition is genuinely hard.~~ Retired — the platform absorbed it.** This risk assumed a hand-rolled FLIP loop. Same-document View Transitions went Baseline in October 2025 and React 19.2 ships `<ViewTransition>`, so the browser does the measurement and interpolation. What remains is a naming-collision problem, not an animation problem. See [transformations.md](transformations.md).

The residual risk is smaller and worth naming: `view-transition-name` must be unique per document at transition time, and naming every block in a 12-scene experience will both collide and tank performance. Name only what's in the viewport.

**3. 18 primitives × 3 ADs = 54 design surfaces.** The single largest cost in v2, larger than the AD system itself. Build primitives last, in demand order, and be willing to ship v2 with 14.

**4. Per-AD budgets couple copy to art direction.** "Content is independent of styling" becomes "content is *mostly* independent of styling." This is an honest crack in the thesis, and the flagged-overflow design is the mitigation: the coupling is surfaced to the user rather than hidden.

**5. Still no users.** Everything in the bets table may be wrong. Ship v1, watch what breaks, then re-read this document before building any of it.
