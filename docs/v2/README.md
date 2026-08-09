# v2 — creative range

> Same content, radically different experiences, one click. This is the release that proves the art-direction abstraction was real.

**Start here:** [spec.md](spec.md) → "What v2 changes from v1".

v1 ships one art direction, so the central bet is untested — a token layer with a single set of tokens is indistinguishable from hard-coded styling. v2 is the falsification test: three art directions, four motion vocabularies, and a reskin that must not break a single layout.

## Files

| Doc | What's in it |
|---|---|
| [spec.md](spec.md) | Theme, commitments vs bets, the locked decisions, **the composition deltas**, platform reality, the deltas from v1, build order, verification, risks |
| [plan/](plan/README.md) | **The implementation plan.** Eighteen phases from one art direction to three, each with what to read, what to build, and what to verify. Build status lives in its README |
| [art-direction-system.md](art-direction-system.md) | **The AD format.** DTCG alignment, budgets, brand mapping, the 3 hand-authored ADs, motion as an independent axis, user controls, the linter |
| [transformations.md](transformations.md) | Reskin and its transition, overflow handling, compare view, motion swap, slides mode, version history |
| [primitives.md](primitives.md) | The 7 new blocks — `Gallery`, `Timeline`, `Comparison`, `Marquee`, `LogoWall`, `SpecTable`, `ScrollSequence` — plus `Chart`, reversed out of the refusal list, and what stays refused |

## Find it fast

| If you need… | Go to |
|---|---|
| What to build first, and what blocks what | [plan/README.md](plan/README.md) → "Dependency graph" |
| How far through the build you are | [plan/README.md](plan/README.md) → "Status" |
| What v1's art-direction #2 work already delivered against this plan | [plan/README.md](plan/README.md) → "What v1 already delivered" |
| The six non-negotiables v2 adds to the eleven | [plan/README.md](plan/README.md) → "Rules that apply to every phase" |
| The full `ArtDirection` type | [art-direction-system.md](art-direction-system.md) → "The format" |
| Per-AD character budgets, and why they exist | [art-direction-system.md](art-direction-system.md) → "The format" (cinematic-dark 60, editorial-light 80, bold-brutalist 34) |
| How a user's brand color becomes accent, hover, and soft variants | [art-direction-system.md](art-direction-system.md) → "The format" (OKLCH + `color-mix`) |
| The three ADs, concretely | [art-direction-system.md](art-direction-system.md) → "The three hand-authored art directions" |
| Why motion is a separate axis from visual style | [art-direction-system.md](art-direction-system.md) → "Motion as an independent axis" (3 ADs × 4 vocabularies = 12 combinations) |
| What the linter rejects, and the dual contrast standard | [art-direction-system.md](art-direction-system.md) → "The AD linter" (WCAG 2.2 AA floor + APCA gate) |
| Why the linter is also a security control | [art-direction-system.md](art-direction-system.md) → "The linter is also the injection boundary" |
| The render → screenshot → critic loop, and why it lands in v2 | [spec.md](spec.md) → "The visual verification loop arrives here" |
| How the reskin transition works | [transformations.md](transformations.md) → "Reskin" (View Transitions, Baseline since Oct 2025) |
| What happens when content overflows a tighter budget | [transformations.md](transformations.md) → "Reskin" |
| Slides mode, and what degrades in it | [transformations.md](transformations.md) → "Slides mode" |
| A new primitive's props | [primitives.md](primitives.md) — one section per block |
| What was proposed and rejected | [primitives.md](primitives.md) → "Not added, and why" |
| **Why the output looked thin, and the five phases that fix it** | [spec.md](spec.md) → "Composition deltas" |
| Why a scene shares the viewport with the next one, and the fix | [plan/13-scene-fit.md](plan/13-scene-fit.md) |
| The gradient and neon bans, and what replaces them | [plan/14-texture-without-gradient.md](plan/14-texture-without-gradient.md) |
| Why every `Image` block renders a grey rectangle | [plan/15-images.md](plan/15-images.md) |
| Why charts stopped being refused | [primitives.md](primitives.md) → "The chart reversal, in full" |
| Why generated pages are eight centred scenes in a row | [plan/17-composition.md](plan/17-composition.md) |

## The thing to understand about v2

The per-AD **character budget** was introduced here to make reskin safe — copy that fits `editorial-light` at 80 characters must not break `bold-brutalist` at 34.

That mechanism turns out to be what makes v3's localization possible at all: transcreation translates *within* a budget rather than translating and then fixing overflow ([../v3/localization.md](../v3/localization.md)). A constraint added for one reason paying off somewhere unrelated is the strongest available signal that the abstraction is right.

## Connects to

| | |
|---|---|
| [../v1/README.md](../v1/README.md) | The schema, the renderer, and the single AD this release generalizes |
| [../v3/ai-art-direction.md](../v3/ai-art-direction.md) | v3 derives ADs by filling in v2's four control axes — same format, same linter |
| [../security/content-and-web.md](../security/content-and-web.md) | User-authored ADs introduce CSS token injection, the threat that arrives with this release |
| [../techstack/frontend.md](../techstack/frontend.md) | How motion actually ships to a published page |
| [../techstack/pipeline-tools.md](../techstack/pipeline-tools.md) | The visual verification loop in full — tiers, cost, and where it runs |

**Infrastructure in v2: one addition.** Docker Compose grows the **`render` service** — the visual verification loop needs the renderer and Playwright in one process, and Python cannot server-side-render React ([../techstack/backend.md](../techstack/backend.md)). That also makes v2 the release where `@d-design/schema` is published properly rather than file-linked, since `render` is the second TypeScript consumer. Everything else is application work; AWS lands with v3, which is the release that has users.

*Corrected while writing [plan/00-foundations.md](plan/00-foundations.md): this section previously read "unchanged from v1", which contradicted [spec.md](spec.md) → Build order. The spec was right.*
