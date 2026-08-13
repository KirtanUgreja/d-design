# Phase 09 — design-engine

> This phase makes true that the design space is large enough to make two decks visibly different — 30+ families, still data, still structural.

**Depends on:** 01 · **Blocks:** 10, 11, 12, 13, 15 · **Spec step:** Locked decisions → design space

## Search

**Read first** — docs/findings.md → Model behaviour (mode collapse; diversity is architecture), docs/v1/plan/00-foundations.md (the registry skeleton), docs/coderules/patterns.md (rule 1)

**Grep for** — the design registry, the `Deck` schema, the v1 family count

**Verify externally** — the DTCG token format (from findings.md Platform) for interchange; whether a 30+ family registry can stay hand-authored or needs generation

## Make

Grow the design registry from ~10–15 to 30+ families. Each family remains a tuple of discrete axes (type pairing, layout archetypes, spacing rhythm, texture, color system, motion vocabulary) — a *combination*, not a theme.

### Design decisions

- **30+ families stay data, validated by Pydantic.** The registry is the single source of visual truth, and the no-styling invariant is why it can be: the model never emits presentational values, so the family is the only way a slide gets its look.
- **The axes are the diversity lever, not the count.** The finding from findings.md: typography and layout carry more identity than color. So families vary most on type pairing and layout grammar; color is the axis a viewer attributes to the brand rather than the tool. The registry's diversity budget follows that.
- **DTCG tokens for interchange.** The families can express tokens in the DTCG format for tool interchange (Figma, Style Dictionary), but the renderer consumes them as CSS custom properties. One source, two views.
- **Family generation is a v2 consideration, not a v1 one.** The first 30 are hand-authored with the diversity budget; if that becomes the bottleneck, a generator (offline DSPy, per ai-stack) is the trigger.

## Verify

- [ ] 30+ families, validated
- [ ] Families differ on type and layout axes more than on color
- [ ] Two sampled families have distinct fingerprints
- [ ] **Human:** the registry reads as 30+ distinct design systems, not 30+ variations of one

## Skipped

- Family generation — deferred until the hand-authored 30+ is proven; trigger named above
- The full DTCG import/export tooling — v3

## Exit gate

- [ ] 30+ distinct families, validated
- [ ] Diversity budget follows the type/layout > color finding
- [ ] Family fingerprints distinct
