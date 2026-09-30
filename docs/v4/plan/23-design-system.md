# Phase 23 — design system

> This phase makes true that no two decks share a look: themes are sampled from a real registry instead of hand-specified, and they keep phase 22's quality.

**Depends on:** 22 · **Blocks:** 25 · **Spec step:** Locked decisions → Diversity · **Size:** M

## Search

**Read first** — [../design-engine.md](../design-engine.md) → Registry, "Sampler and theme", [../../design/brand.md](../../design/brand.md) → the collision section, [../../findings.md](../../findings.md) → "Measured in this codebase"

**Grep for**
- `git show cbfebfa^:web/src/features/renderer/texture/patterns.ts` — the mask tiles to port (without the bloom).
- `git show cbfebfa^:web/src/features/art-direction/resolve-brand.ts` — brand colours into roles.
- `contrast_ratio` in `api/pipeline/mapping/brand_tokens.py` at `v3-final`.

**Verify externally**
- The OFL status of each candidate family, from its own licence file, and whether it carries a Reserved Font Name.
- OKLCH and `color-mix()` support dates, if any token relies on them at runtime.

## Make

- 30–40 families in `api/library/fonts/`, each with `meta.json`; about 24 pairings.
- ≥6 palette strategies in OKLCH with guaranteed WCAG 2 + APCA contrast.
- 5 grids, ≥8 motifs (the texture port), 6 image treatments, and the scale, edge, density and motion axes.
- `design/sampler.py`: seeded, compatibility rules, deck-type priors, the three most distant looks.
- `design/theme.py`: axes → `Theme`. **No model call.**
- `design/tiles.py`: style tiles from exemplars and the deck's real title.
- `design/brand.py`: brand colours into roles, hue kept, lightness corrected.

### Design decisions

- **The theme is maths.** A model here would add cost, mode collapse and contrast bugs, and nothing it could add that the sampler cannot.
- **Fonts are embedded as vendored, not subset per deck.** Subsetting is modification under the OFL.

## Verify

- [ ] 1,000 random seeds produce zero contrast failures
- [ ] Every exemplar passes lint and QA under 50 sampled themes
- [ ] The same seed gives the same theme
- [ ] **Human:** 36 tiles on a wall; at least 30 usable, and no trio looks like siblings
- [ ] **Human:** the 12-deck wall with sampled themes; no two decks mistakable

## Skipped

- Logo upload — trigger: phase 29 and the first brand-kit user.
- Per-deck font subsetting — trigger: a non-Latin locale, or fonts over 1 MB of an export.

## Exit gate

- [ ] Phase 22's gate still holds with sampled themes
- [ ] At least 10 pairings and 5 palette strategies appear across the 12 decks
- [ ] Brand colours visibly applied on 2 branded briefs
