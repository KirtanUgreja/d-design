# Art Direction System

v1 had one art direction and no format — the tokens simply were the implementation. v2 needs a format that holds art directions nobody has designed yet, including ones users author.

## The format

```ts
ArtDirection {
  id: string;
  version: number;                 // bumped on any token change
  name: string;
  author: 'system' | 'user';

  type:    TypeTokens;
  color:   ColorTokens;
  rhythm:  RhythmTokens;
  texture: TextureTokens;

  defaultMotion: MotionVocabularyId;
  budgets: ContentBudgets;
  brandMapping: BrandMapping;
}
```

Four token groups instead of v1's five — **motion has left** and become an independent axis. Two new fields carry the weight of everything v2 adds.

### `budgets` — content limits are per-AD

```ts
ContentBudgets {
  eyebrow: number; headline: number; body: number;
  quote: number; stat: number; listItem: number;
}
```

v1 treated character caps as universal. They are not. A 58-character headline is elegant at editorial-light's `clamp(2rem, 4.5vw, 3.5rem)` and catastrophic at brutalist's `clamp(4rem, 12vw, 14rem)`.

Rough shape: `cinematic-dark` 60 · `editorial-light` 80 · `bold-brutalist` 34.

This is the honest crack in the thesis. Content is not fully independent of styling — it is independent of *most* styling, and the residue is character budget. The design response is not to hide the coupling but to surface it: see [transformations.md](transformations.md).

### `brandMapping` — how a brand kit enters this AD

```ts
BrandMapping {
  accentRole: 'accent' | 'bg' | 'ink';    // where brand.primary lands
  allowBrandBackground: boolean;           // may brand color become the bg?
  logoTreatment: 'mono' | 'full-color';
  contrastStrategy: 'lighten' | 'darken';  // direction to correct toward
}
```

Each AD declares how it consumes a brand rather than the brand overriding the AD. `cinematic-dark` maps the brand to accents and stays dark; `bold-brutalist` may make the brand color a full-bleed background. A marketer choosing an art direction is choosing that art direction.

**Contrast correction is not optional.** If a mapped color fails 4.5:1 against its background, the resolver corrects it in the AD's declared direction and uses the original only on non-text surfaces. Shipping unreadable text is worse than deviating from a brand hex, and the user is told it happened.

### `version` — published pages don't move

An AD reference is `{ id, version }`, not a string. Publishing pins the version.

Improving `cinematic-dark` in month 8 cannot restyle a live launch page. The editor offers "update to latest" with a side-by-side preview; the user decides. For a marketer, a page that changes overnight is a support incident, not a delight.

---

## The three hand-authored art directions

Three, not two — two points define a line, and you will mistake AD-specific tokens for universal ones. The third is what tells you the format is right.

### `cinematic-dark` — carried from v1

Deep space, large light type, slow confident motion, grain and glow. Forgiving of sparse content. Full token values in [v1/art-direction.md](../v1/art-direction.md). In v2 it gains `budgets`, `brandMapping`, `version: 1`, and loses its motion tokens to `cinematic-slow`.

### `editorial-light` — the opposite corner

Light ground, serif display against a grotesque text face, tight columnar grid, hairline rules, generous margins, restrained motion. Reads premium and trustworthy.

```
--bg           #FBFAF8      warm off-white, never pure white
--bg-elevated  #FFFFFF
--ink          #16171A
--ink-muted    rgba(22,23,26,0.60)
--hairline     rgba(22,23,26,0.12)
budgets.headline  80         roomier type, longer headlines work
texture           none — no grain, no glow, no gradient
```

Chosen as AD #2 precisely because it is hostile to `cinematic-dark`'s assumptions: light instead of dark, serif instead of sans, restraint instead of atmosphere, no texture at all. Anything shared between these two is genuinely universal.

### `bold-brutalist` — the stress test

Oversized type, hard color blocks, zero gradients, thick rules, mechanical snap motion, extreme contrast.

```
--bg           brand.primary at full strength (allowBrandBackground: true)
--ink          computed black or white, whichever passes contrast
type.hero      clamp(4rem, 12vw, 14rem), tracking -0.05em, weight 800
rhythm         dense — half the scene padding of cinematic-dark
budgets.headline  34         type is enormous; brevity is structural
texture        none, but hard-edged color blocking at the layout level
```

This one breaks things. `allowBrandBackground` exists because of it. The 34-character budget exists because of it. Expect more discoveries — that is why it is AD #3 and not a v3 idea.

---

## Motion as an independent axis

```ts
MotionVocabulary {
  id: string; version: number;
  ease: string; easeEmphasis: string;
  durations: { reveal: number; emphasize: number };
  distances: { revealY: number; parallaxFactor: number };
  stagger: number; staggerCap: number;
  trigger: number;                            // viewport fraction
  slidesVariant: { durations, trigger: 'advance' };
  reducedMotion: { duration: number };        // opacity only
}
```

Four vocabularies:

| | Character |
|---|---|
| `cinematic-slow` | 900ms expo-out, 32px rise, 120ms stagger. From v1 |
| `editorial-restrained` | 500ms, 16px rise, minimal parallax. Motion you notice only if you look |
| `mechanical-snap` | 220ms, hard cubic ease, no parallax, 60ms stagger. Feels engineered |
| `physics-playful` | Spring-based, overshoot, 90ms stagger. Buoyant |

3 ADs × 4 vocabularies = **12 combinations from 7 authored artifacts.** That ratio is the argument for decoupling.

Each AD names a `defaultMotion`, so the surface stays curated — users pick an art direction and get a coherent pairing. The other eleven combinations are there for anyone who wants them.

`reducedMotion` is a required field, not a fallback. `prefers-reduced-motion: reduce` collapses everything to opacity-only. Wire it when motion is first implemented; retrofitting means touching every component.

---

## User-authored art directions

Four control axes. Users never see a token.

| Axis | Range | Drives |
|---|---|---|
| **Density** | airy ↔ packed | Scene padding, spacing scale, measure, budgets |
| **Contrast / mood** | dark ↔ light, soft ↔ hard | Color roles, texture intensity |
| **Type character** | serif ↔ geometric ↔ grotesque, restrained ↔ aggressive | Font pairing, scale ratio, tracking, weight |
| **Motion energy** | slow-cinematic ↔ snappy-mechanical | Selects or interpolates a motion vocabulary |

Four axes because these are the four that change how a design *feels* rather than how it looks in detail. A fifth would be a knob for something users cannot perceive.

Output is a full `ArtDirection` with `author: 'user'`, stored in the same table as the hand-authored ones. Same format or the format is wrong.

**Budgets are derived, not set.** Density and type character determine how much text fits; asking a user for a character budget would be asking them to do arithmetic on a design.

---

## The AD linter

Any AD from a control panel — and later from AI derivation — can produce unreadable garbage. Same philosophy as scene validation: make bad output unrepresentable rather than asking nicely.

**Hard failures. An AD that fails cannot be saved.**

| Rule | Bound |
|---|---|
| Text contrast | `ink`/`bg` and `ink-muted`/`bg` ≥ 4.5:1; large display ≥ 3:1 |
| Accent contrast | ≥ 4.5:1 wherever accent carries text |
| Type scale monotonic | `hero > section > lead > normal ≥ muted > eyebrow` |
| Scale range | `hero / normal` between 2.5 and 8 |
| Line height | display ≥ 0.85; body between 1.4 and 1.8 |
| Measure | between 45ch and 80ch |
| Spacing scale | strictly increasing, adjacent ratios between 1.2 and 2.0 |
| Motion duration | between 120ms and 1400ms |
| Reduced motion | present, opacity-only, ≤ 300ms |
| Budgets | headline between 20 and 120 characters |

Every bound has a reason. `hero/normal < 2.5` produces a design with no hierarchy; `> 8` produces a headline with orphaned body text. Line height below 1.4 on body text fails readability; above 1.8 the paragraph stops cohering. These aren't taste — they're the range outside which the renderer produces something nobody would defend.

**Test the linter with a deliberately broken AD** — 2:1 contrast, non-monotonic scale, 4-second durations — and require every rule to fire.

---

## Forward commitment: how v3 derives ADs from references

AI-derived art directions are v3, but the stance was decided during v2 design and is recorded here so v3 does not re-litigate it.

**Extract abstract qualities only.** A user drops in a screenshot, a site, or a moodboard, and the system derives:

- density and spatial rhythm
- contrast and mood
- type *character* — serif vs geometric vs grotesque, restrained vs aggressive
- motion energy

It never extracts fonts, exact colors, or literal layouts.

Two reasons, and the second matters more. A tool that clones a reference site's design is a plagiarism machine with your name on it. And derived-by-quality output is simply better — it produces an art direction in the *spirit* of the reference, adapted to the user's own brand kit, rather than a worse copy of someone else's page.

Note that these four extraction targets are exactly the four user control axes above. That is deliberate: v3's derivation is not a new system, it is the AI filling in the same four controls a user could set by hand. If v2's control axes are right, v3's derivation is mostly a perception problem — and if they're wrong, v2 will reveal it long before v3 is built.
