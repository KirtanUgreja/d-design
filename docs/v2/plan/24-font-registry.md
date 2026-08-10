# Phase 24 — The font registry

> Six font families is the tightest ceiling in the product and the most visible one. Typography carries more identity than any other axis, and it currently has six values. This phase takes the registry to 40+ families and a few hundred **vetted pairs** — which is mechanical work, not clever work, and buys more variety than any other single change available.

**Depends on:** [01](01-ad-format.md) · **Blocks:** [21](21-art-direction-engine.md) · **Spec step:** variety delta

Read [../variety.md](../variety.md) first. This phase implements fix 1 and does not restate its argument.

---

## Why this is the highest-leverage phase in the release

A person who cannot name a single typeface can still tell two decks apart by their type. Colour is the axis a viewer attributes to *"the brand"* — and in this product colour largely comes **from** the brand kit. Typography is what is left, and it is what makes a deck look like a *different piece of design* rather than the same design recoloured.

Six families produce roughly a dozen tasteful pairs. That is a smaller reachable space than Gamma's 25 curated themes, and no amount of model intelligence widens it — the model can only pick from what the registry holds.

**It also has no runtime cost.** Two families ship per deck, so a 40-family registry is storage, not bundle size, and [20](20-offline-and-export.md)'s one-file download is unaffected.

---

## Search

**Read first**

- [../variety.md](../variety.md) → "The measurement" and fix 1
- [../art-direction-system.md](../art-direction-system.md) → the `font` token group and how a slot binds to a family
- [../../v1/art-direction.md](../../v1/art-direction.md) → "The result", which records *why* the registry became keyed by family rather than by role. That change was made for exactly this phase's benefit, one release early

**Grep for**

- `api/schema/art_direction.py` → `FontFamilyName = Literal[...]` and `VETTED_FONT_FAMILIES`. The `Literal` is the ceiling; a 40-value `Literal` is legal but is the wrong shape and this phase decides that
- `web/src/features/art-direction/art-direction.ts` → `FONT_REGISTRY`, keyed by family, with per-family `weights`. **The comment above it explains the keying decision** — read it before changing the shape
- `web/src/features/art-direction/art-direction.test.ts` → the tests asserting family names and available weights. These are the guard against a pair naming a weight the file does not contain
- `@fontsource` usage and `package.json` in `web` and `render` → how families are actually installed today, and what 40 of them does to install time
- `docs/coderules/dependencies.md` → **40 font packages is 40 ledger lines** unless they are handled as one entry. Decide which before installing anything

**Verify externally**

- **Licence for every family before it enters the registry.** SIL OFL explicitly permits bundling and embedding in commercial products including SaaS, provided font files are not sold on their own — which covers the published deck, the PDF and the offline bundle. **Verify per family**; "it is on Google Fonts" is not a licence check, and a handful of popular faces are not OFL
- Reserved Font Names under OFL — they constrain *derivative* naming, not use. Confirm nothing in the pipeline renames or subsets in a way that triggers it
- Variable-font availability per family. A variable font is one file for every weight, which changes the storage arithmetic and is worth preferring where it exists

---

## Make

```
api/schema/art_direction.py     FontFamilyName stops being a hand-written Literal
api/schema/fixtures/fonts.json  the registry: families, weights, classification
api/features/art_direction/
  pairs.py                      vetted pairs, and the rules a pair must satisfy
```

### Families, then pairs — and pairs are the deliverable

**40 families is not 1,560 pairs.** It is a few hundred *vetted* ones. An arbitrary display/text combination is usually bad, and shipping the combinatorial product would replace "everything looks the same" with "everything looks wrong", which is not an improvement.

Each family carries enough metadata for a sampler to reason about it without opening a font file: classification (serif / grotesque / geometric / display / mono), a character axis (restrained → aggressive), available weights, whether it is variable, and its licence.

A **pair** is a display family, a text family, and the character it produces together. Pairs are hand-authored — this is where the taste bottleneck moves, and it is a far better use of hand-authoring time than a fourth complete art direction, because one pair contributes to hundreds of decks and a fourth art direction contributes to one shelf slot.

### `FontFamilyName` stops being a hand-written `Literal`

A 40-value `Literal` maintained by hand in a Python file, cross-checked against a TypeScript registry, is the shape that was correct at six and is wrong at forty. The families become data with the fixture as the authority, and the cross-language check that exists today — `web`'s registry failing to compile if it names a family the schema does not — has to survive the change in some form. **If that check cannot survive, keep the `Literal`**; it is worth more than the tidiness.

### The linter learns about pairs

An art direction naming a pair that is not vetted is a hard failure. An art direction naming a weight the family does not ship is already a failure and stays one — that test exists and is the model for this rule.

---

## Verify

**The gate** — green, and the schema regenerates with no diff.

**The registry**

- [ ] 40+ families, each with a verified licence recorded **in the fixture, per family** — not a blanket statement in a ledger line
- [ ] Every family loads and renders in `web`, `render`, and an offline bundle
- [ ] A few hundred vetted pairs, each hand-checked. **Look at every one at hero size and at body size.** A pair that works at 8rem and dies at 1rem is not a pair
- [ ] No pair names a weight its families do not ship. The existing test extends rather than being duplicated
- [ ] The three existing art directions are unchanged — their pairs are in the registry and still resolve identically. This is the check that proves the widening was additive

**The point of the phase**

- [ ] The distinguishable-look count is computed and written down: pairs × ground polarities × texture kinds. **If it did not move by an order of magnitude, the phase did not work**
- [ ] Install time and repository size are measured before and after, and recorded. 40 font packages is a real cost and it should be a known one

**Boundaries**

- [ ] Bundle size for a single deck is unchanged — still two families
- [ ] The offline bundle still embeds only the two families the deck uses. Greppable
- [ ] Dependency ledger updated with whatever shape was chosen, and the choice is explained

---

## Skipped

| Not built | Trigger |
|---|---|
| User-uploaded fonts | v3, with the brand kit. It is a licence and a validation problem, not a registry problem |
| Commercial / paid foundry licences | When revenue justifies it. OFL covers enough range to make this phase work, and a paid face cannot ship in a downloadable bundle without a specific licence |
| Generating or modifying typefaces | Never |
| Arbitrary display/text combinations | Deliberate. Vetted pairs only — the combinatorial product is mostly bad |
| Per-script fonts for non-Latin | [../../v3/localization.md](../../v3/localization.md). This phase must not make that harder — record the script coverage each family has while the data is in front of you |

---

## Exit gate

- [ ] 40+ families, licence verified and recorded per family
- [ ] A few hundred vetted pairs, each looked at by a person at two sizes
- [ ] The three existing art directions resolve identically to before
- [ ] Distinguishable-look count computed and up by an order of magnitude
- [ ] Per-deck bundle size unchanged; offline bundle embeds two families
- [ ] Cross-language family check survives, or the `Literal` stays
- [ ] The gate is green
