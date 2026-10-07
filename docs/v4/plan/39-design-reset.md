# Phase 39 — design reset: plan, references, images, ranked candidates

> This phase makes true that a deck looks designed by a person *and* unlike other decks: a visible style plan per deck, each slide adapted from a strong reference rather than invented from nothing, imagery in one consistent style, several candidates per slide ranked by measured design quality, and nothing decorative that does not serve the message.

**Depends on:** 36, 37 · **Replaces:** the 2026-10-08 shape experiment · **Size:** L · **Owner's ask:** 2026-10-08 — "this looks very bad and everything feels messy… update our whole system accordingly" · **Evidence:** [../research-2026-10.md](../research-2026-10.md)

## Why

The owner's two walls of 2026-10-08: the gate run was **one house style** (Designed 3.5, Varied 3.1); the art-direction run was **messy**. The literature and Gamma 5 agree on the cause: a model designing every slide from nothing either collapses to its favourite look or, pushed for variety, produces noise. Quality comes from **references, a plan, imagery and selection** — not from more freedom.

## Make

1. **A style plan the user sees** (Gamma 5's "highest-leverage moment"). With the outline, the user sees the deck's direction: a name, a one-line idea, three example slides rendered small, and the image style. "Another style" regenerates it. No menu to pick from: one generated direction, changeable.
2. **A reference library, adapted not filled** (PPTAgent, SlideCoder). About 120 slide designs at first — **many visual languages**, each tagged by content shape (one number, comparison, sequence, quote, statement, chart, team…) and by style traits. Per slide, code retrieves 2–3 that fit the content shape *and* the deck's direction; the model **adapts** one to this deck's tokens and words. The archive and novelty gate (phase 36) stop the same reference repeating across decks. Made by: the design model drafting candidates in many styles, **the owner keeping only the ones he would present** (design-engine.md's original "taste asset").
3. **A layout plan before HTML** (DeepSlides). The model first returns a small JSON plan — reference id, grid areas, block roles, the image's place, the emphasis — validated by code (every field placed, sizes legal, the deck's rhythm rules); then writes HTML inside it.
4. **Imagery in one style per deck** (phase 25's image half, moved here). A style chosen with the direction (editorial photo, illustration, line art, collage, abstract), one cheap image model, an image on roughly half the slides, placed by the plan (full-bleed, half, inset, background with an overlay). No text in images; a failed image becomes no image, never a broken slide.
5. **Several candidates, ranked by measurement** (AeSlides, LayoutPrompter). 2 candidates per slide, both rendered; ranked by computed scores — balance, collisions, empty-space quality, alignment to the grid, clutter, contrast — plus a pairwise vision check for taste only, never the sole gate.
6. **Targeted repair** (ReDeck): fix the failing block, not the slide.
7. **Remove what made it messy**: free decorative shapes (`dd-shape`) only where a reference uses them; the generated motif textures become rare; the small-label-plus-accent-line habit is no longer in any reference.
8. **A compose-model bake-off** (the owner, 2026-10-08): 3–4 cheap, creative models on the same 4 briefs, scored on the wall.

### Design decisions

- **References are not templates.** A template is filled; a reference is adapted into this deck's type, colour, imagery and words, and the archive refuses repeats. This keeps the owner's 2026-10-05 rule (no stored layout reused as-is) while giving the model what every strong system has: something good to start from.
- **The owner's taste is the library's gate.** No reference enters without his keep.
- **Imagery is a design element, not decoration**: one style per deck, placed by the plan, never generic stock-looking filler (Gamma's most-cited weakness).

## Verify

- [ ] 120 references, at least 8 visual languages, every one passing QA under 50 looks
- [ ] Retrieval returns a fitting reference for every bench slide
- [ ] Candidates: the ranker's choice agrees with the owner's pick on a 40-pair blind test at least 70% of the time
- [ ] **Human:** a 12-deck wall — Designed ≥ 4.2 and Varied ≥ 4.0 (from 3.5 and 3.1), and the owner calls no deck messy

## Cost

About $0.35–0.55 a deck (two candidates, about five images, the plan call) — inside the $0.80–1.70 budget in bench.md. The library is drafted once (about $3–5) and curated by the owner.

## Exit gate

- [ ] The owner's wall clears the Verify line
- [ ] Median deck cost ≤ $0.60
