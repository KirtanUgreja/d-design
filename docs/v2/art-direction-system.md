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
  rhythm:  RhythmTokens;        // + fit, fitMinBlock, fitPlace
  texture: TextureTokens;       // six kinds, none of them a ramp

  composition: CompositionTokens;   // splits, ground cycle, measures
  furniture:   FurnitureTokens;     // scene index, rules, running label
  image:       ImageTreatment;      // how a photograph joins this AD
  chart:       ChartTokens;         // series fills, grid, labelling

  defaultMotion: MotionVocabularyId;
  budgets: ContentBudgets;
  brandMapping: BrandMapping;
}
```

Motion has left v1's five and become an independent axis. Two of the remaining fields — `budgets` and `brandMapping` — carry the weight of everything v2's original scope adds.

**The four groups in the middle were added on 2026-08-09** ([../v2/spec.md](spec.md) → "Composition deltas"), and each one exists because a value that should have been the art direction's turned out to be hardcoded in the renderer or absent entirely: `1fr 1fr` in every split, a radial bloom behind every hero, a grey rectangle for every image, and no answer at all for a trend. Their full definitions live with the phases that build them — [13](plan/13-scene-fit.md) for `rhythm.fit`, [14](plan/14-texture-without-gradient.md) for the texture union, [15](plan/15-images.md) for `ImageTreatment`, [16](plan/16-charts.md) for `ChartTokens`, [17](plan/17-composition.md) for `composition` and `furniture`.

They are not a separate kind of thing. Every one is read by a `var()` the same way `--bg` is, none introduces a branch, and rule 12 holds unchanged: **an art direction is still tokens only.** What changed is how much of the design those tokens actually cover — which was the honest answer to "why do two art directions look like two colour schemes."

### Speak DTCG for the parts that map

The **W3C Design Tokens Community Group format reached its first stable version (2025.10) in October 2025** — media type `application/design-tokens+json`, file extensions `.tokens` / `.tokens.json`. It is supported or being implemented by Figma, Sketch, Framer, Penpot, Style Dictionary, Tokens Studio, Supernova, and zeroheight, with editors from Adobe, Google, Microsoft, Salesforce, Shopify, and others.

**Store the primitive layer in DTCG format.** Colors, dimensions, durations, cubic-béziers, font families, and shadows all have standard DTCG types. Doing this costs nothing now and buys three things:

| | Why it matters |
|---|---|
| **Designers can author an AD in Figma or Tokens Studio** and export it | The `author: 'user'` path stops being "move four sliders" and becomes "bring your real design system" |
| **v4's marketplace gets an interchange format for free** | An AD becomes a portable file rather than a row in your database |
| **Style Dictionary and Terrazzo can transform it** | You don't write the CSS-variable emitter |

DTCG has no concept of `budgets`, `brandMapping`, `defaultMotion`, or scene semantics — and shouldn't. Those live in the spec's `$extensions` field, which exists for exactly this. The AD record is therefore **a DTCG token file plus a semantic wrapper**, not a proprietary format that happens to hold tokens.

Do not over-invest here in v2. The win is choosing a shape that doesn't have to be migrated later; a full round-trip with Figma is a v4 concern.

**An imported token file is external input**, and the import path is the one most likely to be treated as trusted because it came from a designer's tool rather than a text field. It gets the same Zod parse and the same grammar validation as anything typed into the control panel — see the linter below.

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

### Derive the palette in CSS, not in JavaScript

One brand color has to become a family: accent, accent-soft, hover, focus, disabled, glow. Historically that meant a build step or a JS color library. It no longer does.

`color-mix()` is **Baseline Widely Available** (~89% global support), OKLCH is at ~87%, and relative color syntax — `oklch(from var(--accent) l c h)` — has shipped in every major browser. The current best practice for design systems is exactly this shape: **one source-of-truth brand color, functional tokens derived from it at runtime.**

```css
--accent:       var(--brand-primary);
--accent-soft:  color-mix(in oklch, var(--accent) 12%, transparent);
--accent-hover: oklch(from var(--accent) calc(l + 0.08) c h);
```

Two reasons this matters more here than in a normal design system:

**OKLCH is perceptually uniform, so lightening actually lightens.** Nudging `l` in OKLCH moves perceived lightness predictably; the same operation in HSL shifts saturation and hue in ways that wreck a brand color. Contrast correction below depends on this being well-behaved.

**Reskin becomes cheaper.** Swap `--brand-primary` and every derived token follows automatically — there is no per-AD palette to recompute, and no JS pass to run inside the View Transition.

### Contrast correction, and why WCAG 2 is the wrong tool for the flagship AD

**Contrast correction is not optional.** If a mapped color fails against its background, the resolver corrects it in the AD's declared direction and uses the original only on non-text surfaces. Shipping unreadable text is worse than deviating from a brand hex, and the user is told it happened.

But *fails against* needs a definition, and the obvious one is wrong for this product:

> **WCAG 2.x contrast cannot be used for guidance designing dark mode.**

WCAG 2's ratio is polarity-blind — it scores light-on-dark and dark-on-light identically, when the eye does not perceive them the same way. That is why dark themes routinely pass 4.5:1 on paper and read muddy in practice. `cinematic-dark` is the flagship art direction and is dark by definition, so the standard everyone reaches for first is the one least able to evaluate it.

**APCA** (Accessible Perceptual Contrast Algorithm) is polarity-aware, reports a lightness contrast `Lc` value on a roughly ±106 scale, and is the algorithm **WCAG 3.0 will adopt**. WCAG 3.0 remains a draft; WCAG 2.2 remains the standard that legal and procurement teams check against.

So the linter runs **both**, for different jobs — see the rules table below.

### `version` — published pages don't move

An AD reference is `{ id, version }`, not a string. Publishing pins the version.

Improving `cinematic-dark` in month 8 cannot restyle a live launch page. The editor offers "update to latest" with a side-by-side preview; the user decides. For a marketer, a page that changes overnight is a support incident, not a delight.

---

## The three hand-authored art directions

Three, not two — two points define a line, and you will mistake AD-specific tokens for universal ones. The third is what tells you the format is right.

### `cinematic-dark` — carried from v1

Deep space, large light type, slow confident motion, grain and glow. Forgiving of sparse content. Full token values in [v1/art-direction.md](../v1/art-direction.md). In v2 it gains `budgets`, `brandMapping`, `version: 1`, and loses its motion tokens to `cinematic-slow`.

### `editorial-light` — the opposite corner

> **Built in v1, and its ground is cool rather than warm.** The sketch below says `#FBFAF8`, warm off-white. [../design/brand.md](../design/brand.md) requires the opposite — our own chrome is warm paper, and if the two converge the site stops looking like a neutral wall and starts looking like it is wearing one of the three things we sell. `brand.md` won; the shipped ground is a cool `#fbfcfd`. Treat the value below as superseded and the character description as accurate.

Light ground, serif display against a grotesque text face, tight columnar grid, hairline rules, generous margins, restrained motion. Reads premium and trustworthy.

```
--bg           #FBFAF8      warm off-white, never pure white
--bg-elevated  #FFFFFF
--ink          #16171A
--ink-muted    rgba(22,23,26,0.60)
--hairline     rgba(22,23,26,0.12)
budgets.headline  80         roomier type, longer headlines work
texture           weave + rule — v1 took the empty array because the only
                  three kinds all assumed a dark ground. Phase 14 gives it
                  two that read on paper, so "none" stops being the answer
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
texture        halftone at full strength, riso misregistration, hard rules
composition    ground cycle inverts on alternate scenes — this is where the
               "hard-edged colour blocking" lives, as a token the existing
               layouts read rather than as a layout the AD supplies
```

This one breaks things. `allowBrandBackground` exists because of it. The 34-character budget exists because of it. Expect more discoveries — that is why it is AD #3 and not a v3 idea.

**"Hard-edged colour blocking at the layout level" was the most suspicious sentence in this document**, because layout belongs to the scene and rule 12 is what reskin's whole promise rests on. It resolves as [17](plan/17-composition.md)'s `groundCycle`: an ordered list of palette roles indexed by scene position. A lookup indexed by position is not a branch, the AI never sees it, and the layouts are untouched — which is what [plan/04](plan/04-three-art-directions.md) said the honest answer would have to look like if there was one.

---

## Typography mechanics every AD inherits

These are renderer-level, not per-AD — but they are what makes a hard character budget read as *deliberate* rather than *cramped*, so they belong next to the budgets that depend on them.

**`text-wrap: balance` on every headline.** Baseline since 2024 (Chrome 114+, Edge 114+, Firefox 121+, Safari 17.5+). It distributes a heading evenly across its lines and eliminates the "staircase" — one long line followed by a two-word orphan. Paired with `clamp()` fluid sizing it keeps a heading visually centered and weighted at any viewport.

This is the mechanical partner to the character budget. The budget guarantees a headline is short enough to set well; `balance` guarantees it actually does. Together they're why a 34-character brutalist headline looks composed instead of truncated.

Note the implementation limit: browsers cap `balance` at a small number of lines (Chrome around four) for performance. That's fine here — anything longer has already blown its budget.

**`text-wrap: pretty` on body copy.** A more expensive algorithm aimed at the last lines of a paragraph, preventing single-word orphans. Support is narrower — Chrome 117+, Edge 117+, Safari 26+, **not Firefox as of early 2026** — so treat it as progressive enhancement. Nothing breaks without it.

**Optical sizing where the typeface offers it.** Variable fonts with an optical-size axis (Fraunces, Recursive, and most modern serif families) adjust letterform contrast and spacing as size changes — tighter apertures and finer strokes at display sizes, sturdier ones at body sizes. This is a meaningful part of why editorial typography looks professionally set, and it costs one declaration. Where an AD's display face has custom axes, they belong in that AD's type tokens.

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

| Rule | Bound | Standard |
|---|---|---|
| **Text contrast — compliance floor** | `ink`/`bg` and `ink-muted`/`bg` ≥ 4.5:1; large display ≥ 3:1 | WCAG 2.2 AA |
| **Text contrast — perceptual gate** | body `Lc ≥ 75`; large display `Lc ≥ 60`; incidental/disabled `Lc ≥ 45` | APCA |
| Accent contrast | both of the above, wherever accent carries text | both |
| Type scale monotonic | `hero > section > lead > normal ≥ muted > eyebrow` | — |
| Scale range | `hero / normal` between 2.5 and 8 | — |
| Line height | display ≥ 0.85; body between 1.4 and 1.8 | — |
| Measure | between 45ch and 80ch | — |
| Spacing scale | strictly increasing, adjacent ratios between 1.2 and 2.0 | — |
| Motion duration | between 120ms and 1400ms | — |
| Reduced motion | present, opacity-only, ≤ 300ms | — |
| Budgets | headline between 20 and 120 characters | — |
| **No ramp** | no token value serializes to a string containing `gradient`. There is no token whose type could produce one | rule 18 |
| **No bloom** | no token value produces a blur radius or a chromatic shadow. A hard offset shadow at zero blur is permitted | rule 19 |
| **Saturation bound** | a colour carrying text or used at small size, at OKLCH `C > 0.20` **and** `L > 0.72`, on a ground below `L 0.30` → rejected | rule 19 |
| Ground cycle | every role in the cycle passes both contrast gates with the AD's ink, including inverted scenes | [17](plan/17-composition.md) |
| Split ratio | each side between 0.25 and 0.75 of the whole; the narrow side has a `measureShort` between 28ch and 50ch | [17](plan/17-composition.md) |
| Chart series | 4 entries, each a palette role plus a fill, and no two entries identical on **both** axes | [16](plan/16-charts.md) |
| Chart value labels | pass APCA against their own mark's fill, including halftone and hatch, where the effective ground is not flat | [16](plan/16-charts.md) |
| **Token grammar** | every value parses as its declared type and re-serializes | [../security/content-and-web.md](../security/content-and-web.md) |

### The linter is also the injection boundary

The rules above are design rules. **One more class is a security rule, and it enters with this release**, because v2 is the first version where a token value is not written by you.

A token value becomes a CSS custom property, and art directions require `style-src 'unsafe-inline'`. An unvalidated token is therefore a script-adjacent injection point on a page carrying a customer's brand.

**Every value is parsed by type and re-serialized. Nothing is passed through as a string.**

| Token kind | Validation |
|---|---|
| Colors | Parsed into a color object, re-serialized. Never the original string |
| Numbers | Numeric, range-checked against the bounds above |
| Enums | Matched against known values, rejected otherwise |
| **Font families** | **Selected from a curated registry by id. Never a user-supplied string** |
| Easing curves | `cubic-bezier(a,b,c,d)` with numeric components, or a known keyword |

Rejected outright: `url(`, `expression(`, `@import`, `</style`, `javascript:`, backslash escapes, and any character outside the expected grammar.

Font families deserve the emphasis. A family name is the most natural-looking free-text token in the system and the one most likely to be waved through — which is why they are ids into a registry that maps to a vetted family and file. It also happens to be what v3's per-script font stacks need anyway ([../v3/localization.md](../v3/localization.md)), so the registry is not overhead bought for security alone.

**These are hard failures, exactly like a contrast violation. One validator, two purposes** — and building it as one is what stops the security half from being skipped as separate work. An uploaded DTCG file is external input and gets one Zod parse at the boundary ([../coderules/README.md](../coderules/README.md), rule 2); the linter runs on the parsed result.

**Why two contrast standards and not one.** They answer different questions. WCAG 2.2 AA is what an enterprise accessibility audit will run and what a procurement checklist will cite — it is the floor you cannot ship below, regardless of whether it measures the right thing. APCA is what tells you a dark art direction is *actually readable*, which WCAG 2 structurally cannot. Passing only WCAG 2 yields muddy dark themes that clear the audit; passing only APCA yields a beautiful page that fails a customer's compliance review.

Run WCAG 2 as the hard legal floor and APCA as the quality gate. When they disagree, APCA is almost always the one telling you something true about `cinematic-dark`.

Every other bound has a reason too. `hero/normal < 2.5` produces a design with no hierarchy; `> 8` produces a headline with orphaned body text. Line height below 1.4 on body text fails readability; above 1.8 the paragraph stops cohering. These aren't taste — they're the range outside which the renderer produces something nobody would defend.

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
