# Phase 14 — Texture without gradient

> Colour changes by dot, line, dither and hard edge — never by ramp, never by bloom. The ban already exists for our own surfaces; this is the phase where it starts applying to the thing we ship.

**Depends on:** [01](01-ad-format.md) · **Blocks:** [03](03-ad-linter.md), [04](04-three-art-directions.md), [15](15-images.md), [16](16-charts.md) · **Spec step:** delta — see [../spec.md](../spec.md) → "Composition deltas"

---

## The finding this phase starts from

[../../design/principles.md](../../design/principles.md) principle 5 bans, outright and not "sparingly": *purple→pink gradients*, *neon, glow, bloom*, *gradient text*, *glassmorphism over a blurred mesh blob*. That list has always been read as a rule about **our chrome and our marketing site**.

The artifact does not obey it. As shipped in v1:

| Where | What |
|---|---|
| `renderer/scene.tsx` | The `glow` texture is `radial-gradient(ellipse at 50% 0%, var(--accent-soft), transparent 60%)` — a coloured bloom behind every hero |
| `renderer/scene.tsx` | The `vignette` texture is a second radial gradient |
| `renderer/blocks/gradient-mesh.tsx` | Named for the technique. Four radial gradients, screen-blended |
| `renderer/blocks/visuals.tsx` | `orb` is a two-stop radial gradient; `noise-veil` is a linear gradient; `grid-lines` fades through a radial mask |

Four of five `AbstractVisual` generators and two of three texture kinds are gradients, and one of them is literally a coloured bloom. **The product's own principle 5 indicts its output**, and the reason it went unnoticed is that principle 5 lives in `docs/design/` where the audience is our site.

So the correction is not a new opinion. It is applying an existing one to the layer that was exempted by filing:

> **Principle 5's banned list governs the artifact, not only the chrome.** A page we generate for a customer is a page carrying our judgement.

And the replacement is not "less texture". Texture is what makes a sparse scene look designed rather than empty ([../../v1/plan/11-visuals-and-slot.md](../../v1/plan/11-visuals-and-slot.md)), and removing it without replacing it produces flat colour and worse output. The replacement is **the same colours, carried by pattern instead of by ramp** — halftone, hatch, dither, grain, weave, hard-edged blocks. That vocabulary is also, as of 2026, where serious work actually is: tactile, print-derived surfaces read as deliberate where a mesh gradient reads as a template ([Artcoast](https://artcoastdesign.com/blog/halftone-textures-neo-print-trend-2026), [Fireart](https://fireart.studio/blog/the-best-web-design-trends/)).

---

## Search

**Read first**

- [../../design/principles.md](../../design/principles.md) → principle 5, the whole table. It is the specification for this phase and it is already written
- [../../v1/art-direction.md](../../v1/art-direction.md) → "Texture", and the `VisualBlend` / `VisualStrength` story. The mechanism that composites a texture onto a ground is correct and is not being replaced
- [../art-direction-system.md](../art-direction-system.md) → "The texture vocabulary", rewritten by this phase
- [../../security/content-and-web.md](../../security/content-and-web.md) → "CSS injection via art-direction tokens". Every pattern below is a mask; the colour comes from a token. That is not a stylistic choice

**Grep for**

- `web/src/features/renderer/blocks/visuals.tsx` — the four generators, and `visual-seed.ts`'s single PRNG and intensity scale. **The seed logic is not rewritten**; the paint is
- `web/src/features/renderer/blocks/gradient-mesh.tsx` — the fifth, and the file that is deleted
- `web/src/features/renderer/scene.tsx` → `Texture`. Three hardcoded layers with `textureVar` opacities
- `web/src/features/art-direction/art-direction.ts` → `TextureLayer`, and the comment block explaining why the union is closed at three. That comment is right, and this phase is the moment it describes: *"if art direction #3 wants a texture that is not one of those three, that is the moment to design the vocabulary properly rather than add a fourth `if`"*
- `api/schema/scene.py` → `AbstractVisualProps.generator`. A schema `Literal`, so changing it is a migration
- `scripts/checks/invariants.sh` — six checks today. This phase adds the two that make rules 18 and 19 real

**Verify externally**

- `mask-image` support. Unprefixed CSS masking is Baseline; confirm whether the `-webkit-` prefix is still needed for the minimum Safari this product supports, because the whole vocabulary rests on it

---

## Make

```
web/src/features/renderer/texture/
  patterns.ts             the shape library — data-URI SVG masks, colourless
  texture-layer.tsx       one component, one kind, driven by tokens
web/src/features/renderer/blocks/
  visuals.tsx             the six generators, rewritten
  gradient-mesh.tsx       deleted
web/src/features/renderer/
  scene.tsx               Texture reads the AD's layer list instead of three literals
web/src/features/art-direction/
  art-direction.ts        the new TextureLayer union
  cinematic-dark.ts       re-authored: the glow becomes a stepped dot bloom
api/schema/scene.py       the generator Literal
api/migrations/versions/  generator id migration
scripts/checks/invariants.sh   checks 8 and 9
```

### 1. The mask carries the shape, the token carries the colour

Every pattern is a **colourless** SVG in a data URI, used as `mask-image`. The colour underneath is a CSS custom property.

```tsx
{ maskImage: `url("${PATTERN.halftone}")`, maskSize: 'var(--texture-scale)',
  backgroundColor: 'var(--accent)' }
```

This is not stylistic. A data-URI SVG cannot resolve `var()`, so the alternative is interpolating a token value into a URI-encoded string — which is exactly the pass-a-token-through-as-a-string that rule 13 forbids, in the most easily missed place available. Masking makes the correct thing also the easy thing: `patterns.ts` holds no colours at all, and a pattern that wanted one could not have it.

`to-css-vars.ts` stays the only token→string path.

### 2. The vocabulary — six kinds, and the union stays closed

```ts
type TextureLayer =
  | { kind: 'grain';    intensity: number; scale: Length }
  | { kind: 'halftone'; intensity: number; scale: Length; angle: number; steps: 2 | 3 | 4 }
  | { kind: 'hatch';    intensity: number; scale: Length; angle: number; cross: boolean }
  | { kind: 'dither';   intensity: number; scale: Length; steps: 2 | 3 | 4 }
  | { kind: 'weave';    intensity: number; scale: Length }
  | { kind: 'rule';     intensity: number; axis: 'block' | 'inline'; weight: Length };
```

| kind | Reads as | Replaces |
|---|---|---|
| `grain` | Film emulsion, paper tooth. `feTurbulence`, unchanged from v1 | — |
| `halftone` | Print, engineered, deliberate. A dot lattice at a fixed angle | `glow` |
| `hatch` | Engraving, technical drawing. Parallel rules; `cross` gives cross-hatch | — |
| `dither` | Ordered Bayer 4×4. Two-tone shading with no ramp anywhere | `vignette` |
| `weave` | Canvas, uncoated stock. The quietest kind, and the one that reads on white | — |
| `rule` | Hairline structural rules. Promoted from *"editorial-light takes the empty array"* into a real answer | — |

`glow` and `vignette` are **removed from the union**, not deprecated. A kind that cannot be expressed without a ramp does not get to exist, and leaving it in the type is how it comes back.

Six is a real increase over three, and [../../v1/art-direction.md](../../v1/art-direction.md) is explicit that a fourth kind is a renderer change and therefore a real cost. **This phase pays that cost deliberately, once**, because three kinds that all assume a dark ground and a light source is the gap that doc already recorded and declined to fill. After this phase the union is closed again on the same terms.

### 3. Shading happens in steps, never continuously

This is the aesthetic rule that keeps the vocabulary honest, and it is what `steps` is for. A halftone that fades by continuously shrinking its dots is a gradient with extra work. Coverage changes across **2 to 4 discrete bands with hard edges** — the same way a risograph or a newspaper does it.

`cinematic-dark`'s hero glow becomes a three-step dot bloom: a dense dot field at the light source, a middle band, a sparse band, hard boundaries between them. On a black stage it reads as light with a printed grain, and it is unmistakably not a mesh.

The vignette becomes a dithered edge: Bayer dissolve from the ground colour inward, in three bands. This is the classic non-gradient vignette and it looks like a choice, which the radial one never did.

### 4. Riso misregistration is free range

Two texture layers of the same kind, in two token colours, offset by a small token distance and composited with the AD's `visualBlend`. Colour, texture and depth with no gradient and no third mechanism — it falls out of the layer list, which is the sign the layer list is the right shape.

`bold-brutalist` will want it hard and obvious. `editorial-light` will want a half-millimetre and only on one plate.

### 5. The generators

```
gradient-mesh   →  halftone-field    stepped dot field, seeded placement
orb             →  hatch-drift       engraved line field, seeded spacing
noise-veil      →  dither-fade       Bayer dissolve across the frame
grid-lines      →  grid-lines        kept; its radial fade mask becomes a dither mask
particle-field  →  particle-field    kept; audit it, dots are already dots
                →  block-collage     new: hard-edged colour blocks, riso-offset
```

`visual-seed.ts` — one PRNG, one intensity scale, shared — does not change. The determinism guarantees from [../../v1/plan/11-visuals-and-slot.md](../../v1/plan/11-visuals-and-slot.md) still hold: same seed, same output, across processes and restarts, derived from the scene id.

**The generator enum is a schema `Literal` and a published value**, so this is a migration, not an edit. Map old ids to new ones for existing rows (`gradient-mesh` → `halftone-field`, `orb` → `hatch-drift`, `noise-veil` → `dither-fade`) and keep the mapping in the migration where it can be read, not in application code where it becomes permanent.

### 6. Neon is a lighting effect, not a hue

The ban has to be written precisely or it either bans nothing or bans `bold-brutalist`'s entire premise. A saturated colour is not neon. A saturated colour that **appears to emit light** is.

**Banned as effects, everywhere in `renderer/`:**

- `filter: blur()` and `backdrop-filter` used as bloom
- `box-shadow` and `text-shadow` with a chromatic colour, at any blur radius
- any halo, glow ring, or luminous edge around type or a mark

**Bounded as values, in the linter** ([03](03-ad-linter.md)):

- a colour carrying text or used at small size, at OKLCH `C > 0.20` **and** `L > 0.72`, on a ground below `L 0.30` → rejected. That combination is acid-on-black and nothing else
- `allowBrandBackground` is untouched. A full-strength brand colour as a hard-edged ground is a poster, and posters are the point

Shadows do not disappear from the system — a **hard offset shadow** with zero blur in an ink colour is a print device, not a bloom, and it is what `bold-brutalist` should reach for. The banned property is the blur.

### 7. Make both rules greppable

`scripts/checks/invariants.sh` gains two checks, because rules with no automated enforcement are the ones that erode ([../plan/README.md](README.md) → "Rules that apply to every phase"):

```
7. no `(linear|radial|conic|repeating-*)-gradient(` under web/src/features/renderer
   or web/src/features/art-direction
8. no `blur(`, `boxShadow`, `textShadow`, `dropShadow` under web/src/features/renderer
```

A grep is the right shape here for the same reason `allow-same-origin` is a grep and not a component test: the component's own tests pass with the rule broken. Verify each by breaking it and watching the gate go red.

### 8. The scrim over an image is a veil, not a scrim

Text over media conventionally uses a bottom-up gradient scrim. `--veil` is already a flat alpha and stays one; where a flat veil is too heavy, the answer is a **dithered veil** — the same Bayer mask at two steps — and not a ramp. This connects directly to [15](15-images.md), where every image gets a treatment and the veil becomes part of it.

---

## Verify

**The gate** — green, plus invariants checks 8 and 9.

**The ban**

- [ ] No gradient function anywhere under `renderer/` or `art-direction/`. Check 7, verified by breaking it
- [ ] No blur, no chromatic shadow. Check 8, verified by breaking it
- [ ] `glow` and `vignette` are absent from the `TextureLayer` union — a type error, not a lint warning
- [ ] No token value serializes to a string containing `gradient`. Belongs to the linter and is asserted here too, because this is where it would first appear
- [ ] `patterns.ts` contains no colour. Grep it for `#`, `rgb`, `oklch`, `var(--` and find nothing

**The vocabulary**

- [ ] All six kinds render under both existing art directions, at three intensities, on the AD's own ground **and over a real photograph**. This is the review that found the v1 smudge and it is still the check most likely to be skipped
- [ ] `weave` and `rule` read correctly on white. The three v1 kinds all assumed a dark ground; if the new ones inherit that, nothing was fixed
- [ ] Shading is stepped. Screenshot a `halftone` at `steps: 3` and assert three flat bands with hard boundaries — a continuous falloff means someone reimplemented a gradient out of dots
- [ ] Riso misregistration renders from two layers with no third mechanism

**The generators**

- [ ] Six generators, same seed → identical output, across processes and a restart
- [ ] Seeds still derive from the scene id; a rebuild is not a visual change nobody asked for
- [ ] `assertNoPresentationalValues` still passes — a generator is an enum and a number
- [ ] The migration maps every old generator id, and an experience stored under v1 renders after it

**Human**

- [ ] `cinematic-dark`'s hero, before and after, side by side. The stepped bloom must read as *more* deliberate than the mesh, not as the mesh with a bug. If it reads as worse, the steps are wrong, not the decision
- [ ] Show someone the output and ask what it was made with. "A design tool" is the pass; "an AI thing" is the failure this phase exists for

---

## Skipped

| Not built | Trigger |
|---|---|
| A seventh texture kind | The union closes again after this phase, on the same terms as v1 |
| Per-block texture | Texture is applied at the scene level, never per block. Unchanged from v1 |
| WebGL or canvas-based texture | CSS masks and SVG patterns cost nothing and run in three processes. A shader runs in one |
| Animated texture | Motion is an axis and it belongs to the vocabulary, not to a ground pattern |
| Colour-managed print simulation (true CMYK separation) | It is a nice idea and it is a research project |
| Retiring `accentSoft` | It is a flat alpha fill and it is still legitimate. What it may no longer be is the colour of a bloom |

---

## Exit gate

- [x] Zero gradient functions and zero blurs under `renderer/`, enforced by grep, verified by breaking — eight probes, each caught
- [x] Six texture kinds, all mask-driven, all token-coloured, reviewed on both grounds. **Over photography: not done** — `/dev/visuals` renders over an uploaded photo and there are no uploads without a running `api`
- [x] `glow` and `vignette` removed from the union; `cinematic-dark` re-authored and not merely stripped
- [x] Six generators, deterministic, with `gradient-mesh.tsx` deleted
- [ ] The migration maps every old generator id — **written, unverified.** Docker was not running, so no migration ran and no `api` test ran
- [x] The neon rules exist as effect bans in the renderer. Value bounds are [03](03-ad-linter.md)'s, as this phase always said
- [x] Principle 5's banned list is stated to govern the artifact, in [../../design/principles.md](../../design/principles.md) itself
- [x] The gate is green

## What the build found

**The first render was worse than what it replaced, and that is the review working.** This phase's human check says the stepped bloom must read as *more* deliberate than the mesh, and that if it reads worse the steps are wrong rather than the decision. It read worse: dots covering 80% of their tile at an 11px pitch, over a headline, is not a halftone — it is polka dots fighting the type. Three values were wrong, not the approach: max dot radius (now 4.4 of 16, was 6.4), pitch (6px, was 11), and the vignette's reach, which at 50% inset was most of the frame rather than an edge treatment. Screenshotting and looking is the only thing that catches this; no assertion in this repo would have.

**`editorial-light`'s `rule` layer was deleted after looking at it.** A hairline every 32px across a whole scene reads as ruled notebook paper, and it was worse than the empty array v1 shipped. The error was a category one: in print a baseline grid is *invisible*, and a rule you can see is structural — under a running head, between columns. The kind stays in the vocabulary because `bold-brutalist` will want it, but what v1's note actually asked for is **furniture, not ground**, and [17](17-composition.md) already has `Furniture { rule, ruleWeight }` for it.

**`invariants.sh` had a fail-open, and it disabled every check in the file.** Deleting `gradient-mesh.tsx` left it tracked-but-absent; `git ls-files` still listed it, `grep` exited 2 on the missing path, `xargs` turned that into 123, and `scan` reported "no match". Two brand-new checks passed silently against deliberate violations. **Anyone mid-refactor with an unstaged deletion was running no invariants at all, including the tenant wrapper.** `scan` now decides on output rather than exit code and skips absent files. A second instance of the same shape: `:(exclude)*.test.*` alongside a directory pathspec returns an *empty* file list, so every check written that way also passed unconditionally.

**The documentation trap, for the third time.** Checks 7 and 9 fired on the comments explaining the rules they enforce, which check 6 had already solved once. It is now a `code_scan` helper that drops comment lines and test files, rather than a fourth bespoke regex.

### Deviations

| | |
|---|---|
| `TextureLayer` gains `color`, `scale` and `offset` | The doc's union has none, and section 4 requires two token colours and an offset for riso. `color` is a `ColorRole`, never a value — which is what keeps the pattern a colourless mask |
| `rule.weight` is `'hairline' \| 'thin' \| 'thick'`, not a `Length` | A tile baked into a data URI cannot resolve a token, so a `Length` would have to be interpolated into the URI — the exact rule-13 violation `patterns.ts` exists to make impossible |
| Texture emits **by index**, not by kind | Two layers of the same kind is what riso *is*, and `--texture-halftone-*` cannot hold two of them |
| Texture is exempt from the AD totality test | Every other variable is read unconditionally; a texture variable is read only inside its kind's branch. The round trip replaces the guarantee and is stronger — it reads back exactly the declared fields and throws on a missing one |
| `grid-lines` loses its edge fade rather than gaining a stepped one | The v1 fade was a `radial-gradient` mask. A hard inset frame is the lazy replacement, `ponytail:`-marked; the upgrade path is the ring bands `DitherVignette` already implements |
