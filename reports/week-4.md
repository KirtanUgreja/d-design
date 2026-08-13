# Week 4 — Art direction #2, the presentation pivot, and the v2 foundation

**Dates:** Mon 25 Aug – Sun 31 Aug 2026 · **Status:** v1 done · v2 phases 00–04 and 13–15 done

## What was done this week

Week 3 proved the product path. Week 4 proved the central claim and then re-decided the product's direction from evidence — the acceptance run's reservations, not a preference.

### 1. Art direction #2 — the falsification test
- Built `editorial-light`, the second art direction, the day v1's acceptance run passed.
- The claim under test was specific: the same scene tree, the same 11 primitives, the same 8 scenes — rendered as a black stage with amber light and 8vw type, and as a printed spread with oxide-red rules and a 4.5rem serif. Side by side, one switch apart, with nothing in the scene tree changed.
- **The claim held.** The renderer gained no branch — no `mode`, no `if (artDirection.id === …)`. Seven small costs were paid instead, each one a hardcoded value becoming a token, which is exactly what the architecture is supposed to do.
- The three most distant art directions in the format (`cinematic-dark`, `editorial-light`, `bold-brutalist`) were built deliberately, and the output space was measured: **6 font families, 6 layouts, 6 texture kinds, 53% identical value paths** across the three.

### 2. The presentation pivot
- The re-test of "what is this product" failed on three counts, all from the acceptance run's reservations:
  - the market's loudest complaint (Gamma's broken PowerPoint export) is *caused* by page-shaped layouts meeting slide-shaped output;
  - composition needs a bounded frame — a slide has one, a page does not;
  - the live room is the harder design case nobody has made beautiful.
- **The artefact is a presentation, not a scrolling page.** The scene tree does not change, the token layer does not change shape, and the renderer's purity does not change — the pivot is a change of default, frame, and surrounding features.
- The user is now the person *in the room*: a founder or salesperson pitching live, where the deck decides money.

### 3. v2 — planned and started
- v2 was planned in 25 phases: the art-direction engine (generate three art directions from a brand or reference instead of choosing from a shelf), motion as an axis, one-click reskin, version history, a presentation frame that works 4:3 to 21:9, presenter view, offline and export, charts, and more.
- Built the v2 foundation: the three migrations, the render service, and the render image.
- Built the AD format v2 with brand derivation in CSS, motion as an independent axis (3 art directions × 4 motion vocabularies), and the AD linter — which found three defects in the flagship direction.
- Fixed what the first generated output made visible: a scene owns its frame, texture without gradient, and images that exist (two renditions and a srcset, wired through the one seam).
- Added the five phases the output demanded (13–17) — scenes-as-a-stage, texture, images, charts, composition — and corrected the docs to match what actually shipped.

## This week's deliverables
- Art direction #2, proving the variety claim with no renderer branch.
- The presentation pivot: the product re-decided as a deck, argued from the market and the acceptance run.
- The v2 plan (25 phases) and the first built phases: migrations, render service, AD format v2, motion axis, AD linter, three art directions, scene-as-stage, texture, and images.

## Next week's plan
- Finish the v2 foundations already in flight: budgets in the pipeline, version history, and the one-click reskin.
- Build the visual critic — the mechanism that looks at rendered output, because the automated gates verified structure while every real defect was presentational.
- Build the presentation frame (4:3–21:9, no letterboxing) and presentation playback.
- Build the art-direction engine — three art directions generated from a brand or reference, which is the feature no template tool can copy.
- Continue through the v2 plan: composition, charts, presenter view, offline and export, deck length, and the phone remote.
