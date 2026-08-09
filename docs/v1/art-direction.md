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

In v1 every token value is hand-authored by you, so its shape is not a security question. **It becomes one in v2**, when users author art directions, and more so in v3 when the AI derives them from an attacker-supplyable reference — a token value becomes a CSS custom property, and art directions require `style-src 'unsafe-inline'`. From v2 every value is parsed and re-serialized by type before it becomes CSS ([../security/content-and-web.md](../security/content-and-web.md), [../v2/art-direction-system.md](../v2/art-direction-system.md)). Worth knowing while designing the token groups: **a token whose type is "any string" is a token that will have to be redesigned.**

## The claim this layer makes

Same 11 primitives, same scene tree, unrecognizably different output — because everything that makes a design feel a certain way lives here, not in the components.

**v1 does not prove this.** One art direction proves nothing about variety. The proof is art direction #2, and the test is specific: if it requires *any* renderer change, the abstraction is wrong and should be fixed before a third exists.

### The result: `editorial-light`, built 2026-08-09

**The claim holds, with one correction to how the test is worded.** Two art directions now render the same fixture tree — the same eleven primitives, the same eight scenes — as a black stage with amber light and 8vw type, and as a printed spread with oxide-red rules and a 4.5rem serif. Side by side on `/dev/primitives`, one switch apart. Nothing in the scene tree changed and no block component learned a second way to lay anything out.

But "any renderer change" turned out to be the wrong bar, and reading it literally would have produced a worse system. Two files under `renderer/` did change, and both changes were **a hardcoded value becoming a token** — which is what the paragraph above this one instructs ("if a component needs a number the tokens don't provide, the token set has a gap — fill the gap, don't hardcode"). The sharper test, and the one to apply to art direction #3:

> Did the renderer gain a **branch** — a `mode`, an `if (artDirection.id === …)`, a second layout path? Then the abstraction is wrong. Did it gain a **token read**? Then the token set had a gap, which is the exercise working.

It gained no branches. Here is the whole cost, in the order it was found:

| What #2 cost | Where | Why it had been invisible |
|---|---|---|
| **The types split from the values** | `art-direction.ts` split out of `cinematic-dark.ts` | With one instance, the instance and the interface are the same file and nothing makes you notice |
| **The font registry was global** | keyed by role (`display`/`text`) → keyed by family, with each direction binding the two slots | Two families were "the" two families. A second direction could change every size and colour and was still stuck with Fraunces and Inter |
| **The brand resolver only lightened** | `resolve-brand.ts` picks a direction from the ground's luminance | Correct on near-black, exactly backwards on near-white: a failing brand colour moved *toward* the background and was then reported unreachable. Its own test asserted this as "fail-closed" |
| **`mix-blend-mode: screen`, seven times** | → the `visualBlend` token | `screen` keeps what is lighter than the backdrop. Phase 11 reviewed the generators over a photograph and fixed them *into* a dark-ground assumption. On paper they were invisible |
| **The visual layer's loudness** | → the `visualStrength` token | Only visible once the blend was fixed: a saturated ink at cinematic-dark's 45% is a stain rather than atmosphere |
| **Two `@fontsource` families** | `dependencies.md` | — |
| **One `Literal` value** | `api/schema/experience.py` | — |

Four of those seven are the same shape: **a value the renderer or the token layer held globally, because "global" and "cinematic-dark's" were indistinguishable while there was one.** That is the real lesson for #3, and the reason #3 should be cheap in a way #2 was not.

**What was deliberately not paid for.** The texture vocabulary is a closed union of three kinds — grain, glow, vignette — each with one renderer implementation and only intensity varying. All three assume a dark ground and a light source, so on white every one of them is dirt. `editorial-light` takes the empty array and gets its structure from hairline rules instead, which is a real answer rather than a gap papered over; a fourth kind would be a renderer change of the branching sort and was not taken. If art direction #3 wants a texture that is not one of those three, that is the moment to design the vocabulary properly rather than add a fourth `if`.

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

**Spacing tokens are applied through logical properties**, always — `padding-inline`, `margin-block-start`, `border-inline-start`. Never `padding-left`. The tokens themselves are direction-agnostic numbers; what matters is that the renderer never spends one on a physical axis. This costs nothing in v1 and is what makes v3's RTL a `dir` attribute instead of an audit of every primitive ([../v3/localization.md](../v3/localization.md)).

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

**Motion is the one place logical properties do not save you.** `transform` operates on x/y and ignores block/inline entirely, so any horizontal translate has to invert manually under RTL. The exception list is short enough to test exhaustively, and it is worth writing down now rather than rediscovering it in v3:

| | RTL |
|---|---|
| `reveal` — `translateY` | unchanged |
| `parallax` — `translateY` | unchanged |
| any `translateX` | **inverts** |

v1 has no RTL, so nothing here is v1 work. Knowing which axis is a liability is what keeps a horizontal reveal from being added carelessly ([../v3/localization.md](../v3/localization.md)).

### How this is implemented

**Motion** (the library formerly called Framer Motion — renamed in 2025, package `motion`, import path `motion/react`) drives the reveals. The old `framer-motion` package still installs but is no longer actively developed; use `motion`.

**CSS scroll-driven animations are not Baseline yet** and cannot be the primary mechanism. As of mid-2026, `animation-timeline` / `scroll-timeline` / `view-timeline` sit at roughly 84% global support: Chrome 115+, Edge 115+, Safari 18+ — but Firefox stable still keeps it behind the `layout.css.scroll-driven-animations.enabled` flag, which has blocked Baseline since September 2025.

So: **JS-driven reveals as the floor, CSS scroll-driven animation as progressive enhancement.** Author the finished state as the default, layer the animation on top; a browser that doesn't understand `animation-timeline` ignores the declaration entirely. Never author the *hidden* state as the default — a Firefox user must not get a blank page.

### Reduced motion is a design requirement here, not a checkbox

This matters more for this product than for most. Parallax scrolling — foreground and background moving at different rates — is a documented trigger for vestibular disorders: nausea, dizziness, headaches. An art direction built on cinematic scroll motion is, without care, actively hostile to those users.

**WCAG 2.3.3 Animation from Interactions (Level AAA)** covers exactly this: motion triggered by user interaction must be disableable. Scroll is an interaction, so parallax falls squarely under it.

Two controls, both required:

1. **`prefers-reduced-motion: reduce`** collapses every intent to opacity-only, 200ms, no transform, no parallax. Wire it when motion is first implemented — retrofitting means touching every component.
2. **An in-page motion toggle.** The OS-level setting is the standard mechanism and most people don't know it exists. Published guidance is explicit that a page-level control should accompany it, and for a product whose entire premise is heavy motion, shipping only the media query leaves affected viewers with no recourse on someone else's launch page.

The toggle belongs in the runtime, so every published experience gets it for free — not something each art direction re-implements.

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
