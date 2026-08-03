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
| AD linter with hard failures | User-authored ADs can produce unreadable pages carrying your name |
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

**Migration:** existing v1 experiences get `artDirection: { id: 'cinematic-dark', version: 1 }` and the v1 caps become that AD's budgets. No content changes. The `scenes` jsonb shape is otherwise unchanged.

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
3. AD linter (contrast, scale monotonicity, motion bounds)
4. **Hand-author `editorial-light`**
5. **Hand-author `bold-brutalist`** — this is where missing tokens surface
6. Version history / snapshots
7. Reskin + overflow report + shorten-with-AI
8. Reskin transition animation — *the delight budget*
9. Compare view
10. Remaining motion vocabularies: `editorial-restrained`, `mechanical-snap`, `physics-playful`
11. Slides mode — reuses the overflow mechanism from step 7
12. The 7 primitives, in order of real demand

Do not build reskin (7) before both new ADs exist (4–5). Reskin against one AD is untestable, and the second and third ADs are what tell you the format is wrong while it's still cheap to change.

## Verification

| What | How |
|---|---|
| **AD format completeness** | All 3 ADs express fully in the format with zero renderer changes. **If any AD needs a renderer change, the abstraction is wrong — stop and fix it.** |
| **Linter** | Feed it a deliberately broken AD (2:1 contrast, non-monotonic scale, 4s durations). Every rule must fail it. |
| **Reskin matrix** | 3 ADs × 4 motion vocabularies × 2 modes = 24 combinations against 5 golden experiences. All must render valid, no crashes, overflow correctly reported. |
| **Version pinning** | Publish under AD v1, bump AD to v2, confirm the published page is byte-identical. |
| **History** | Reskin, restore, assert the tree is identical to the pre-reskin snapshot. |
| **Slides overflow** | Content that fits a scroll scene and not a slide is flagged, never silently clipped. |
| **Primitives** | All 18 rendered under all 3 ADs. Visual judgment — 54 surfaces, and this is the real cost of v2. |

## Risks

**1. Three ADs may prove the token schema wrong.** That is the *purpose* of steps 4–5, not a failure of them. Budget for a format refactor between AD #2 and AD #3, and treat needing one as the process working.

**2. The reskin transition is genuinely hard.** Animating a whole page between two token sets means FLIP-style measurement, and text reflow does not interpolate. See [transformations.md](transformations.md). It is also where the delight budget goes, so it cannot be skipped — but it can ship as a fast cross-fade first and get beautiful later.

**3. 18 primitives × 3 ADs = 54 design surfaces.** The single largest cost in v2, larger than the AD system itself. Build primitives last, in demand order, and be willing to ship v2 with 14.

**4. Per-AD budgets couple copy to art direction.** "Content is independent of styling" becomes "content is *mostly* independent of styling." This is an honest crack in the thesis, and the flagged-overflow design is the mitigation: the coupling is surfaced to the user rather than hidden.

**5. Still no users.** Everything in the bets table may be wrong. Ship v1, watch what breaks, then re-read this document before building any of it.
