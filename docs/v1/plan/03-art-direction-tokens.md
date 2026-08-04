# Phase 03 — Art direction, the code half

> Five token groups, a motion vocabulary, and a brand resolver that will not ship unreadable text. The renderer reads only this. If a component ever needs a number the tokens do not provide, the token set has a gap.

**Depends on:** [02](02-art-direction-design.md) · **Blocks:** [04](04-renderer.md) · **Spec step:** 2, code half

---

## Search

**Read first**

- [../art-direction.md](../art-direction.md) — all of it, and treat its values as the starting point phase 02 has now superseded
- [../../security/content-and-web.md](../../security/content-and-web.md) → "CSS injection via art-direction tokens" — v1 does not have this threat, and the token *types* designed here are what decide whether v2 has it
- [../../coderules/patterns.md](../../coderules/patterns.md) → rule 2, so the reduced-motion mechanism is designed correctly the first time

**Grep for**

- `src/schema/scene.ts` — `Motion`, `Layout`, `Region`, and the `emphasis` unions. The token file's keys must be exactly those unions, so a missing role is a type error rather than an undefined CSS variable
- `src/lib/result.ts` — the brand resolver returns a `Result` when a brand colour cannot be corrected into range

**Verify externally** — nothing. This phase is the extraction from phase 02 plus one piece of colour maths.

---

## Make

```
src/features/art-direction/
  index.ts               the public surface: the AD object, the resolver, the vocabulary
  cinematic-dark.ts      the five token groups, typed
  motion-vocabulary.ts   reveal / emphasize / parallax / none, and the reduced variant
  resolve-brand.ts       brand kit → semantic roles, contrast-corrected
  to-css-vars.ts         token object → CSS custom property bundle
  art-direction.test.ts
```

### Token types are the decision, not token values

[../art-direction.md](../art-direction.md) says it in one line and it is the most consequential sentence in the document: **a token whose type is "any string" is a token that will have to be redesigned.**

v1 hand-authors every value, so nothing here is a security question yet. From v2 users author them and from v3 the AI derives them from an attacker-supplyable reference — at which point every token value is parsed and re-serialized by type before becoming CSS. Design the types now so that is a validator, not a rewrite:

| Group | Type, not string |
|---|---|
| **Color** | A colour object (channels + alpha), re-serialized on emit. Never a hex string passed through |
| **Rhythm** | Numbers with units attached by the emitter, and `clamp()` triples as `{ min, preferred, max }` |
| **Type** | Font by **registry id**, never a family string. Sizes as the clamp triple above. Tracking and line-height as numbers |
| **Motion** | Easing as a parsed `[a,b,c,d]` tuple, durations as milliseconds, distances as numbers |
| **Texture** | Enum: `grain` · `glow` · `vignette` · `none`, with numeric intensity |

The font registry is one object mapping id → vetted family and file. It is four lines in v1 and it is the thing that stops the most natural-looking free-text token in the whole system from ever existing.

### The brand resolver

```ts
resolveBrand(brand: BrandKit, ad: ArtDirection): ResolvedTokens
```

Brand colours **map into semantic roles, they do not replace them**. `cinematic-dark` stays dark under a pastel brand — it applies the brand's accent to a dark system rather than adopting the brand wholesale. A marketer choosing a cinematic art direction is choosing cinematic.

**Contrast is enforced, not hoped for.** If `brand.primary` fails 4.5:1 against `--bg`, lighten it until it passes and keep the original for non-text surfaces only. Silently shipping unreadable text is worse than deviating from a brand hex, and this is the one place the product overrides the customer on purpose.

### The motion vocabulary, and why reduced motion is a prop

The renderer core is pure and may not read `typeof window` ([../../coderules/patterns.md](../../coderules/patterns.md), rule 6). So the reduced-motion collapse **cannot** live inside a block component. It lives in the vocabulary:

```ts
export const CINEMATIC_MOTION: MotionVocabulary          // reveal 900ms, parallax, stagger 120ms
export const REDUCED_MOTION:   MotionVocabulary          // opacity-only, 200ms, no transform
```

The wrapper decides which one to pass. That is why `SceneRenderer(tree, artDirection, motion)` takes motion as a parameter at all, and it is the cleanest demonstration in the codebase of what rule 6 buys.

Two controls are required, not one ([../art-direction.md](../art-direction.md), WCAG 2.3.3):

1. `prefers-reduced-motion: reduce` → the wrapper passes `REDUCED_MOTION`
2. **An in-page toggle** → the same swap, user-initiated. It belongs in the runtime so every published experience gets it for free, not in each art direction

**Stagger is derived from block index within a region, capped at 5.** Never authored, never in the schema. Compute it in the vocabulary, not in each block.

### `to-css-vars.ts`

One function, token object → a CSS custom property bundle applied at the scene root. This is the only place a token becomes a string. That single choke point is what makes v2's grammar validation a change to one file.

---

## Verify

**The gate** — green.

**Tokens**

- [ ] Every key in the token object corresponds to a union member from `src/schema/`. Add a role to `emphasis` without adding a token and it is a type error
- [ ] No token is typed as a bare `string`. Assert it in a test that walks the token object's type — this is the check that stops v2's rewrite
- [ ] `to-css-vars` round-trips: emit, parse the CSS, compare to the source object
- [ ] Every value from phase 02's extracted list is present, and nothing else is

**Brand resolver**

- [ ] A brand primary that fails 4.5:1 against `--bg` comes back lightened until it passes
- [ ] The original, uncorrected colour is still available for non-text surfaces
- [ ] A brand colour that cannot reach 4.5:1 by lightening returns a `Result` failure rather than a best effort — anything that could ship unreadable text fails closed ([../../coderules/patterns.md](../../coderules/patterns.md), rule 5)
- [ ] Under a pastel brand, `--bg` is still near-black

**Motion**

- [ ] `REDUCED_MOTION` produces opacity-only, 200ms, no transform, no parallax — for all four intents
- [ ] Stagger from index caps at 5 siblings
- [ ] The vocabulary contains no `typeof window`, no media-query read, and no environment branch. It is data

---

## Skipped

| Not built | Trigger |
|---|---|
| The AD linter (range and grammar validation) | v2, when users author token values. The *types* it will validate are designed here, which is the whole point of doing them properly now |
| A second art direction | v2. If it requires any renderer change, the abstraction is wrong ([../spec.md](../spec.md), Risk 4) |
| CSS scroll-driven animation | Not Baseline — Firefox still keeps it behind a flag. It is the progressive-enhancement path in phase 04, never the floor |
| View Transitions | React 19.2 has them and v2's reskin is their natural use. Worth knowing it is there; not worth using yet |

---

## Exit gate

- [ ] The three comps from phase 02 can be rebuilt using only tokens from this file, with no literal values
- [ ] No token typed as a bare string; the type test proves it
- [ ] Brand resolver enforces contrast, and fails closed when it cannot
- [ ] Both motion vocabularies exist, and neither reads the environment
- [ ] `src/features/art-direction/index.ts` reads in one screen
