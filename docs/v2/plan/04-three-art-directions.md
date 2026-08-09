# Phase 04 — Three art directions

> `editorial-light` moves into the format. `bold-brutalist` breaks it. This is the phase the whole build order is arranged around, and needing a format refactor here is the process working rather than failing.

**Depends on:** [01](01-ad-format.md), [02](02-motion-axis.md), [03](03-ad-linter.md), [13](13-scene-fit.md), [14](14-texture-without-gradient.md), [15](15-images.md) · **Blocks:** [05](05-budgets-in-the-pipeline.md), [06](06-version-history.md), [12](12-primitives.md), [16](16-charts.md), [17](17-composition.md) · **Spec step:** 4, 5

> **Three added phases land before this one, and each one is a token group these three art directions have to author.** [13](13-scene-fit.md) gives them `rhythm.fit`, [14](14-texture-without-gradient.md) replaces the texture union with six kinds none of which is a ramp, and [15](15-images.md) gives them `ImageTreatment`. Authoring `bold-brutalist` before those exist means re-authoring it after them — the exact repeated cost the "expect the format to be wrong" section below is trying to pay once. [16](16-charts.md) and [17](17-composition.md) go the other way and land *after*, because a chart or a composition token authored against one art direction is that art direction's default wearing a token's name.

---

## Search

**Read first**

- [../art-direction-system.md](../art-direction-system.md) → "The three hand-authored art directions" — the sketched values for both
- [../../v1/art-direction.md](../../v1/art-direction.md) → "The result" — what `editorial-light` already is, and the seven things it cost. **This phase does not re-derive them**
- [../../design/brand.md](../../design/brand.md) → "The collision this decision walks into" — three constraints on `editorial-light` that are not this phase's to relitigate
- [../../design/principles.md](../../design/principles.md) → principle 5, the banned list. `bold-brutalist` is the art direction most likely to reach for a gradient of two violets and call it a statement

**Grep for**

- `web/src/features/art-direction/editorial-light.ts` — it exists, it is authored, and its comment block records why each number is what it is. Migrating it means moving values, not re-choosing them
- `web/src/features/renderer/blocks/` — every primitive. `bold-brutalist` is the stress test, and the ones that break will be `Stat`, `Quote`, `List` and `AbstractVisual`, in that order
- `web/src/features/renderer/tokens.ts` — `VISUAL_BLEND`, `visualOpacity`, `COLOR_VAR`. Three values that used to be hardcoded and became tokens when art direction #2 arrived. If `bold-brutalist` finds a fourth, it belongs here in exactly the same way

**Verify externally**

- Two open-licence display faces on Fontsource that are not Fraunces, not Newsreader, and not whatever our own chrome uses. `bold-brutalist` needs a face with real weight at 12vw, which is a narrower set than it sounds

---

## Make

```
api/features/art_direction/
  seeds/cinematic_dark.tokens.json
  seeds/editorial_light.tokens.json      migrated from the v1 constants
  seeds/bold_brutalist.tokens.json       new
api/migrations/versions/                 seed all three at version 1
web/src/app/globals.css                  + bold-brutalist's two families
docs/coderules/dependencies.md           + the ledger lines
```

### A doc conflict to resolve before authoring `editorial-light`

[../art-direction-system.md](../art-direction-system.md) sketches `editorial-light`'s ground as `#FBFAF8`, **warm off-white**. [../../design/brand.md](../../design/brand.md) requires the opposite: our own chrome is warm paper, so `editorial-light` must be *cool or bright white*, "not both warm".

v1 resolved this toward `brand.md` and shipped a cool `#fbfcfd`. **Keep that resolution and treat the sketch as superseded**, because the constraint has a reason that outlives a colour preference: if our wall and art direction #2 converge, the site stops looking like a neutral wall and starts looking like it is wearing one of the three things we sell.

The other two constraints from `brand.md` are already satisfied by the v1 authoring and should be re-checked rather than re-decided: a display face different from both `cinematic-dark`'s and our chrome's, and an accent much louder than our chrome's two-appearances-per-screen rule.

**The check is concrete, and it is a human one:** put `editorial-light` on the editor canvas with the app chrome around it, and a stranger must be able to tell which pixels are the product and which are the artifact. If they cannot, **the art direction moves**, not the chrome — changing a hand-authored AD costs a day, changing an identity that has leaked into every route and string costs an audit.

### `bold-brutalist` — the one that breaks things

```
--bg           brand.primary at full strength   (allowBrandBackground: true)
--ink          computed black or white, whichever passes both contrast gates
type.hero      clamp(4rem, 12vw, 14rem), tracking -0.05em, weight 800
rhythm         dense — roughly half cinematic-dark's scene padding
budgets.headline  34
texture        none, but hard-edged colour blocking at the layout level
defaultMotion  mechanical-snap … which does not exist yet
```

Three things in that sketch are traps, and naming them now is cheaper than finding them at render time.

**`--bg` from the brand colour means the ink is computed, not authored.** `allowBrandBackground` exists because of this art direction, and the linter's contrast rules now run against a background that is not known until a brand kit is attached. That is a real change to when linting happens: an art direction is lintable on its own, and an art direction *plus a brand* is a second thing that must also be lintable. Build the second check; it is the one that catches a customer's magenta making every headline illegible.

**`defaultMotion: mechanical-snap` is a forward reference.** That vocabulary is phase 11. Point `bold-brutalist` at `cinematic-slow` for now with a `ponytail:` naming the swap, or the seed is a broken foreign key wearing a design decision.

**"Hard-edged colour blocking at the layout level" is the sentence to be most suspicious of in all of v2.** Layout belongs to the scene, not to the art direction — rule 12, and the thing reskin's whole promise rests on. Whatever this turns into, it is a *token* the existing layouts read: a block-level surface colour, a rule weight, an edge treatment. If it cannot be expressed that way, the honest outcome is that `bold-brutalist` does not get it, and that outcome is recorded rather than worked around.

> **It has since been expressed that way.** [17](17-composition.md)'s `groundCycle` is an ordered list of palette roles indexed by scene position, so `bold-brutalist` inverts on alternate scenes with no layout change and no branch — a lookup by position is not a conditional and the AI never sees it. Since 17 lands after this phase, seed `bold-brutalist` with a single ground and a `ponytail:` pointing at the cycle, the same way `defaultMotion` points at a vocabulary that does not exist yet.

### Expect the format to be wrong, and budget for it

Two points define a line, and you will mistake AD-specific tokens for universal ones. **The third art direction is what tells you the format is right**, which is why the spec's Risk 1 says to budget for a format refactor between AD #2 and AD #3 and to treat needing one as the process working.

The v1 exercise found four values held globally because "global" and "cinematic-dark's" were indistinguishable. Expect `bold-brutalist` to find more. Each one follows the same path: **a hardcoded value in the renderer becomes a token in the format**, which is a token read and not a branch.

---

## Verify

**The gate** — green, and the linter passes all three art directions.

**The hard gate for this phase**

- [ ] `bold-brutalist` renders all 11 primitives with **no branch added to the renderer**. No `mode`, no `if (artDirection.id === …)`, no second layout path. A hardcoded value becoming a token is expected and fine; a conditional is the abstraction failing ([../../v1/art-direction.md](../../v1/art-direction.md) → "The result")
- [ ] Every token added in this phase is read by the renderer the same way `--bg` is — through `to-css-vars` and a `var()`, with no art direction named anywhere in `renderer/`

**The art directions**

- [ ] All three pass the linter on every rule, including APCA, and any change made to pass it is a change to the art direction
- [ ] `bold-brutalist` + a hostile brand kit — a mid-grey, a neon, a pastel — still passes both contrast gates, or is refused with a message a marketer can act on
- [ ] All three render the `hostile` fixture without overflowing the viewport. That fixture exists for exactly this
- [ ] `editorial-light`'s migrated record renders byte-identically to its v1 constants

**Security**

- [ ] The three seeds are inserted by migration with `owner_id is null`, and no API path can create a system art direction
- [ ] Both new font families are ids in the registry, imported in `globals.css`, and have ledger lines. A registry row without an import renders as a system fallback and looks like a font-loading bug

**Human — this is most of the phase**

- [ ] Look at all three, full-screen, on the `full` fixture. If two of them feel like the same design at different brightnesses, one of them is not pulling its weight
- [ ] `editorial-light` on the editor canvas with the app chrome around it. A stranger must be able to tell product from artifact
- [ ] `bold-brutalist` must look **deliberate**, not loud. The failure mode is a design that reads as a mistake, and no automated check can tell you which one you have

---

## Skipped

| Not built | Trigger |
|---|---|
| A fourth art direction | v3's user authoring and AI derivation. Three is what proves the format; four is what proves you enjoyed authoring them |
| `mechanical-snap` | [11](11-range.md). `bold-brutalist` points at `cinematic-slow` until then, with a `ponytail:` |
| The four user control axes | Late v2 at the earliest ([../art-direction-system.md](../art-direction-system.md) → "User-authored art directions"). They are the same four v3's AI fills in, which is why they are designed before they are built |
| ~~A texture kind that suits a light or a flat ground~~ | **Built** — [14](14-texture-without-gradient.md) pays that cost deliberately and once, taking the union from three kinds to six. `editorial-light` no longer takes the empty array, and this phase authors real texture for all three |
| `bold-brutalist`'s ground cycle | [17](17-composition.md). Seeded with a single ground and a `ponytail:` until then |

---

## Exit gate

- [x] Three art directions in the store, all passing the linter, all at version 1
- [x] `bold-brutalist` renders every primitive with no renderer branch
- [x] Every value the phase moved out of the renderer is a token the renderer reads generically
- [x] `bold-brutalist` under a hostile brand kit either passes both contrast gates or is refused legibly
- [x] `editorial-light` is distinguishable from our own chrome by a stranger
- [x] Any format refactor this phase forced is recorded in [01](01-ad-format.md)'s file and reflected in the seeds
- [x] The gate is green

---

## What actually happened

**The hard gate held: `bold-brutalist` renders all eleven primitives with no branch added to the renderer.** No `mode`, no `if (artDirection.id === …)`, no second layout path. Two renderer-adjacent things changed and neither is a conditional — one was a hardcoded weight list becoming a token, the other was a genuine layering bug. Both are below.

### The format was wrong in four places, and the third art direction is what said so

Each one is the same shape: **a value the system held globally because it had only ever had one instance of the thing it described.** The plan predicted this and said to treat finding them as the process working ([README](README.md) → "the values a system holds globally").

| What was global | What it actually was | Where |
|---|---|---|
| `REGISTERED_WEIGHTS = [400, 500, 600]` | A property of a *font*, not of the registry. It read as "the weights we self-host" and was really "the weights the first four families happened to want" | `from-record.ts` |
| `BrandMapping`'s four defaults | A stored group nothing read. The moment something did, each default became a value living in two languages | `schema/art_direction.py` |
| The type-scale ceiling of `8.0` | A bound on the wrong quantity — see below | `lint.py` |
| Texture painting above content | Never noticed, because both existing directions' loudest layer is a translucent film | `renderer/scene.tsx` |

**Syne self-hosts one weight and Space Grotesk three.** `clamp(4rem, 10vw, 12rem)` at weight 500 is a large thin headline, not a brutalist one, so art direction #3 needed 800 — and the module constant that had been correct for four families rejected it. Weights are now per-family, which also means a published page pays for the faces it sets rather than for the shape of the first two art directions.

**`brandMapping` lost its defaults entirely.** A Pydantic default generates into `z.enum(…).default(…).optional()`, so filling the `undefined` in TypeScript would have put the same default in two languages — on the group that decides whether a customer's brand colour becomes a page's ground. Requiring all four fields cost three constructor calls and made the boundary a total mapping. An art direction *declaring* how it consumes a brand is the whole idea, and a declaration you can omit is a default wearing the word.

### The linter rule that was measuring the wrong thing

`bold-brutalist` runs `hero` at 11.3× body and the flat ceiling was 8.0. The ceiling's own message said what it was protecting against — *"the headline orphans the body text under it"* — and that is not a property of the ratio. It is a property of how much text is set at that size.

| | hero/normal | headline budget | product |
|---|---|---|---|
| `editorial-light` | 4.50 | 60 | 270 |
| `cinematic-dark` | 7.53 | 60 | 452 |
| `bold-brutalist` | 11.29 | 34 | 384 |

So the bound moved onto the product: **a headline's set width in body-ems**, capped at 520, with the ratio keeping an absolute ceiling of 14 as a backstop so a tiny budget cannot buy an unbounded scale. Two of those three numbers were authored before the rule existed and neither was tuned to it.

**It is stricter than what it replaced, not looser.** 8× body against the 80-character budget [../art-direction-system.md](../art-direction-system.md) sketches for `editorial-light` is 640 and is now refused, where the flat ceiling waved it through. The rule was not relaxed to admit a fashionable art direction; it was pointed at the quantity it had always been trying to measure. A large ratio is not a defect on its own — it is a defect *unpaid for*, and `budgets.headline: 34` is what pays for it.

### The texture layer had been painting on top of the type since phase 14

`<Texture>` is `position: absolute` and a scene's content is in normal flow, and a positioned element paints above its non-positioned siblings. So the ground has been in front of the content for two phases. Nothing showed it, because `cinematic-dark`'s loudest layer is 0.55 opacity and `editorial-light`'s is 0.06 — a film over text is invisible when the film is a film.

`bold-brutalist` set a `rule` layer at intensity 1 in full ink and drew opaque black bars through the headline. Fixed with `z-index: -1` on the layer and `isolation: isolate` on the scene, which are one fix: without the stacking context, "behind" would have meant behind the page.

**This is the most valuable thing the phase produced**, and it is worth naming why it took a third art direction. It is a presentational defect, and every quality mechanism this product has — the schema, the linter, the invariants script, the renderer tests — verifies *structure*. The structure was correct the whole time. That is the same pattern [README](README.md) records for the four defects phases 13–17 exist to fix, recurring exactly where it said it would.

### What the art direction cost that no token can express

**Syne 800 measures 0.864 em per character.** Nearly twice a normal sans. At the sketched `12vw` the word "confidence" did not fit one line at 1440px and broke mid-word, leaving a single orphaned "e" — an aggressive break is a legitimate brutalist device, a one-letter orphan reads as a bug. The hero came down to `clamp(4rem, 10vw, 12rem)`.

Nothing in the format could have predicted it: the linter measures size and budget and cannot know how wide a glyph is. A per-face average advance width is a real token to add the day a fourth family arrives; fitting a constant to one observation is not.

**The `rule` texture kind was authored here and removed after looking at it** — a rule tiled across a whole scene is ruled paper, not structure, and at full ink under a black headline the bars and the letterforms merged into one shape. That is the *same conclusion* `editorial-light` reached in v1 and that [../art-direction-system.md](../art-direction-system.md) already records: **a visible rule is furniture, not ground.** Two of three art directions independently rejecting a texture kind is an argument for `rule` leaving the union and arriving in [17](17-composition.md)'s `Furniture`, where it can be placed once instead of tiled. Noted there rather than acted on here, because removing a kind is a renderer change.

### The brand-as-ground path, and the number that makes phase 17 urgent

`accentRole: 'bg'` is real: a brand kit applied to `bold-brutalist` replaces the page ground at full strength, uncorrected, and `--veil` follows it through a `color-mix()` against `var(--bg)` rather than being recomputed in JavaScript. **An art direction plus a brand is a second thing that has to be lintable**, and `lint_art_direction_with_brand` is it — the art direction's ink against a ground that does not exist until a customer attaches a kit, plus the CTA pair, which is the one that is easy to forget because a CTA label *is* `bg`-coloured text.

Hostile kits are refused with a message written for the person who chose the colour. But the honest number is this:

> **`bold-brutalist` accepts about 2% of the sRGB cube.** Neutrals lighter than `#d8d8d8` pass; a mid-grey, a corporate navy and an oxide red are all refused.

That is a correct consequence of what the art direction *is* — near-black type set directly on your colour — and the exit gate allows a legible refusal. It is also close to useless for a real customer, and the fix is not a better refusal message. It is [17](17-composition.md)'s `groundCycle`: an inverted palette lets a dark brand take white type instead, roughly doubling the range. That was a stylistic argument for phase 17 before this phase and it is a measured one now.

### `contrastStrategy` is read, and phase 01's prediction about it was wrong

Phase 01 deferred the field with "the first one that wants to override is phase 04's `bold-brutalist`". It does not. `bold-brutalist` corrects nothing — the brand goes to the ground at full strength, which is the entire offer — so it has no direction to declare and takes `auto` like the other two.

The field is genuinely read now: `resolveBrand` honours `lighten`/`darken` over the luminance computation, and the test proves it by forcing the *wrong* direction and watching the resolver obey rather than second-guess. `auto` stays better than a declaration for almost every ground; the override exists for a ground sitting near the 0.18 crossover, where the computation has no good answer and a designer does.

### APCA crossed the language boundary, and confirmed phase 03 by accident

`resolveBrand` corrected brand colours until they cleared **WCAG only** — on art directions whose whole premise is a dark ground, which is precisely the standard [../art-direction-system.md](../art-direction-system.md) says cannot judge them. Rule 14 says both gates are hard; the resolver was enforcing half of it. `apcaLc` now lives in `color.ts` alongside the `contrastRatio` that was already duplicated for the same reason, pinned to `lint_contrast.py` by a shared fixture table that now carries **signed** Lc values — a port that dropped the sign would pass a ratio-only table and be wrong about every dark art direction.

It produced one nice piece of evidence. A test fixture had asserted that `#f4b740` passed through uncorrected. That is `cinematic-dark`'s *old* accent, the one phase 03's linter rejected by hand at Lc 70.6. With both gates in the loop the resolver corrects it unprompted and lands on `#f6c667` — within a hair of the `#fcca6d` a person arrived at independently.

### The CTA pair failed a third time

`bold-brutalist`'s accent was authored at `#b81400` and the linter refused it at Lc 66.7 against 75, while WCAG saw 5.11:1 and was content. That is now three art directions out of three where the pair that failed is `bg`-coloured text on an `accent` fill — the one pair no type role describes, and the only place in the system where the ground colour becomes the text. It is not a coincidence and it deserves to be the first thing checked when a fourth art direction is authored.

### Two things I could not test the way I first wrote them

**The CTA-against-a-brand-ground check is unreachable on the shipped art direction.** Its accent is a deep oxide red at OKLCH L 0.34, so any brand light enough to pass the *ground* check contrasts with it easily — the ground check strictly dominates. My first test asserted only that "button fill" appeared in some finding, which passed while both checks were failing together and would have kept passing if the check were deleted. It now lightens the accent to isolate the case.

**The `/dev/primitives` verification was nearly done against a stale server.** `pkill -f "next start"` never matches, because the process renames itself to `next-server`; the page served a six-minute-old build showing the pre-adjustment hero size, and I was one step from concluding the fixture pipeline was broken. Worth knowing for every later phase that verifies in a browser: check the build timestamp against the process start time, not the HTTP status.
