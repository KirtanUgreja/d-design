# Art Direction

The layer that turns intent into values. This is the product's actual differentiator, and the one part of v1 that cannot be delegated.

## What it is

Five token groups. One JSON file plus one CSS-variable bundle per art direction.

| Group | Owns |
|---|---|
| **Type** | Font pairing, scale, line height, tracking, weight, case |
| **Color** | Semantic roles, and how brand colors map into them |
| **Rhythm** | Spacing scale, scene padding, grid, density |
| **Motion** | Easing, duration, distance, stagger, trigger points |
| **Texture** | Grain, glow, gradient, vignette — or none |

The renderer reads *only* these. It contains no hardcoded visual values. If a component needs a number the tokens don't provide, the token set has a gap — fill the gap, don't hardcode.

## The claim this layer makes

Same 11 primitives, same scene tree, unrecognizably different output — because everything that makes a design feel a certain way lives here, not in the components.

**v1 does not prove this.** One art direction proves nothing about variety. The proof is art direction #2, and the test is specific: if it requires *any* renderer change, the abstraction is wrong and should be fixed before a third exists.

## Brand kit integration

The user supplies fonts, colors, and a logo. The art direction decides how they're used.

```
BrandKit { displayFont, textFont, primary, secondary?, neutral?, logoAssetId }
```

Brand colors map into semantic roles, they do not replace them. `cinematic-dark` stays dark even if the brand is a pastel — it applies the brand's accent to a dark system rather than adopting the brand wholesale. A marketer choosing a cinematic art direction is choosing cinematic.

**Contrast is enforced, not hoped for.** If `brand.primary` fails 4.5:1 against `bg`, the resolver lightens it until it passes and uses the original only for non-text surfaces. Accessibility is not negotiable, and silently shipping unreadable text is worse than deviating from a brand hex.

---

# `cinematic-dark`

Deep space, large light type, slow confident motion. Chosen for v1 because it is forgiving of sparse content — negative space reads as intentional rather than unfinished. Editorial-light would expose every spacing mistake while the system is still young.

Reference direction: Apple product pages, Linear's marketing site, Vercel's launch pages. Study them before writing values.

## Color

```
--bg           #08090B          near-black, not pure black
--bg-elevated  #101215          cards, framed media
--ink          #F4F4F5          primary text
--ink-muted    rgba(244,244,245,0.62)
--ink-faint    rgba(244,244,245,0.38)   eyebrows, captions
--accent       brand.primary, contrast-corrected against --bg
--accent-soft  accent @ 12% alpha       glows, fills
--veil         rgba(8,9,11,0.72)        overlay for text on media
--hairline     rgba(244,244,245,0.10)   borders, dividers
```

Pure black is avoided deliberately — it flattens depth and makes glow effects look like artifacts.

## Type

Display font: brand's, or `Instrument Serif` / a tight geometric sans as fallback. Text font: brand's, or `Inter`.

| Role | Size | Line height | Tracking | Weight |
|---|---|---|---|---|
| `hero` | `clamp(3.5rem, 8vw, 8rem)` | 0.95 | -0.03em | 500 |
| `section` | `clamp(2rem, 4.5vw, 3.5rem)` | 1.05 | -0.02em | 500 |
| `lead` | `clamp(1.25rem, 2vw, 1.5rem)` | 1.5 | -0.01em | 400 |
| `normal` | `1.0625rem` | 1.65 | 0 | 400 |
| `muted` | `1.0625rem` | 1.65 | 0 | 400, `--ink-muted` |
| `eyebrow` | `0.8125rem` | 1.2 | 0.14em | 500, uppercase, `--ink-faint` |
| `stat` | `clamp(3rem, 7vw, 6rem)` | 1 | -0.04em | 600 |

Tight negative tracking on large type is most of what separates cinematic from generic. Do not skip it.

## Rhythm

```
--space: 8 · 16 · 24 · 40 · 64 · 96 · 160
--scene-padding-y:  clamp(6rem, 14vh, 12rem)
--scene-padding-x:  clamp(1.5rem, 6vw, 8rem)
--measure:          62ch          max text width
--content-max:      1280px
```

Scenes are generously tall. A cinematic experience earns its pace by giving each beat room; cramming beats is the fastest way to make it feel like a slide deck again.

## Motion

```
--ease:            cubic-bezier(0.16, 1, 0.3, 1)     expo-out
--ease-emphasis:   cubic-bezier(0.22, 1, 0.36, 1)
--stagger:         120ms   per sibling index, capped at 5
--trigger:         25% of element in viewport, fires once
```

| Intent | Behavior |
|---|---|
| `reveal` | opacity 0→1, translateY 32px→0, 900ms `--ease` |
| `emphasize` | opacity 0→1, scale 0.96→1, 1100ms `--ease-emphasis` |
| `parallax` | translateY at 0.15× scroll delta, clamped to ±80px |
| `none` | visible immediately |

Slow is the point. 900ms feels wrong next to typical web UI motion and correct in a cinematic context — resist the urge to speed it up to match app conventions.

**Reduced motion:** `prefers-reduced-motion: reduce` collapses every intent to opacity-only, 200ms, no transform, no parallax. Not an afterthought — wire it when motion is first implemented, because retrofitting it means touching every component.

## Texture

```
--grain:   SVG fractal noise overlay, 4% opacity, fixed position
--glow:    radial-gradient from --accent-soft behind hero content, 60vw
--vignette: subtle radial darkening at viewport edges
```

Applied at the scene level, never per block. Grain especially: one fixed overlay for the whole page, so it doesn't scroll and doesn't multiply.

## Where this gets hard

The tokens above are a starting point, not a finished design. Expect to spend real time on:

- **Type pairing.** The display/text relationship carries most of the character. Get it wrong and no amount of motion polish rescues it.
- **The hero scene specifically.** It's the first thing anyone sees and the only thing most people judge. Design it by hand, against real content, before generalizing to tokens.
- **How `AbstractVisual` generators read against real photography.** Abstract visuals look great on their own and can fight uploaded product shots badly.

Build steps 1–4 exist precisely so this can be evaluated with hand-written scene trees, before a single AI call is wired up.
