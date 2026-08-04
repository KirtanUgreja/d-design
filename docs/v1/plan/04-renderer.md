# Phase 04 — Renderer and the 11 primitives

> The long pole. This is design work, not typing. One pure React tree that will later be used four ways, and the phase whose output decides whether the rest of the product is worth building.

**Depends on:** [03](03-art-direction-tokens.md) · **Blocks:** [05](05-publish-present-embed.md), and hard-blocks [06](06-model-seam-and-build.md) · **Spec step:** 3

> **Do not start phase 06 until this one looks genuinely good.** [../spec.md](../spec.md) says it as an instruction, not a suggestion. Hand-write a scene tree, render it, and look at it — that is the cheapest possible test of the riskiest assumption in the project.

---

## Search

**Read first**

- [../scene-schema.md](../scene-schema.md) → "Block types", "Layouts and regions" — the props each primitive gets and, more importantly, the props it must not have
- [../../coderules/patterns.md](../../coderules/patterns.md) → rule 2, in full. It now runs in three processes from v3
- [../spec.md](../spec.md) → "Two things in step 3 that only pay off two versions later"
- [../../techstack/frontend.md](../../techstack/frontend.md) → "The published artifact" — progressive enhancement is the floor
- [../../security/content-and-web.md](../../security/content-and-web.md) → "The Slot sandbox", "XSS in the renderer"

**Grep for** — this is the phase where duplication starts, and it is worth being deliberate:

- `src/features/art-direction/index.ts` — **every** visual value comes from here. A hardcoded number in a block component means the token set has a gap; fill the gap
- `src/schema/index.ts` — the block prop types. Never re-declare a block's props locally
- `to-css-vars` — the only token→string path. Do not write a second one for the Slot srcdoc; reuse it
- Before writing any layout helper, check whether the previous layout already needed it. Six layouts is exactly the count where an AI writes six near-identical grid helpers

**Verify externally**

- Motion (`motion`, import `motion/react` — **not** `framer-motion`) current major and its React 19 concurrent-rendering support
- `whileInView` trigger semantics against the `--trigger: 25%, fires once` token, so the vocabulary drives the library rather than the library dictating the vocabulary

---

## Make

```
src/features/renderer/
  index.ts                  SceneRenderer, and nothing else worth exporting
  scene-renderer.tsx        the pure core
  scene.tsx                 one scene: layout + regions + texture
  layouts/                  full-bleed · split-left · split-right · centered · stack · grid
  blocks/                   eyebrow · headline · body · quote · list · stat
                            image · video · cta · abstract-visual · slot
  motion/reveal.tsx         the one motion wrapper every block uses
  renderer.test.ts
```

### The signature is the contract

```ts
function SceneRenderer(props: {
  scenes: Scene[];
  artDirection: ArtDirection;
  motion: MotionVocabulary;
}): ReactNode
```

Nothing else. **No `mode`, no `process.env`, no `typeof window`, no branch on where it is running.** The lint rule from phase 00 enforces it; the reason is that from v2 the same components run in the browser, in `web`'s preview renders, and in the `render` service, and a component that behaves differently in one of them is a published page that differs from the edited one.

Everything interactive — selection, fullscreen, the motion toggle, keyboard nav — is a wrapper's job. Interaction lives in the wrappers; rendering lives in the core; they do not mix.

### Logical properties, everywhere, from the first line

`padding-inline`, `margin-block-start`, `inline-size`, `border-inline-start`. Never `padding-left`.

`left` and `right` in the schema name **authoring position, not screen position**. The renderer resolves them logically, so an RTL locale mirrors by setting `dir` and nothing in the schema changes. This has no v1 benefit and is brutal to retrofit across 19 primitives and 3 art directions ([../../v3/localization.md](../../v3/localization.md)).

`transform` is the documented exception, and it is where motion lives. The exception list is short enough to write down now: `translateY` is unaffected by direction; any `translateX` **inverts** under RTL. v1 has no RTL and no horizontal reveal — knowing which axis is a liability is what stops one being added carelessly.

### Progressive enhancement is not optional

**Author the finished state as the default and layer the animation on top.** A reveal animates *in* from a visible resting state, never *out* of `opacity: 0`. An unhydrated `opacity: 0` is a blank page, and a viewer whose JS never arrives must get a finished page without motion rather than nothing ([../../techstack/frontend.md](../../techstack/frontend.md)).

This is one of two decisions in the phase that is expensive to reverse. Get it right in `motion/reveal.tsx` once and every block inherits it.

### The eleven, with the parts that are not obvious

| Block | Notes |
|---|---|
| `Eyebrow` `Headline` `Body` `Quote` | Straight token application. `emphasis` selects a type role, nothing else |
| `List` | 2–5 items, three styles. The `checks` style needs an icon — draw it as inline SVG from tokens, do not add an icon dependency |
| `Stat` | `value` is a **string**. Count-up animates only when it parses as numeric; `"10x"`, `"2.4M"`, `"<50ms"` hold static. Format numerics through `Intl` ([../../coderules/patterns.md](../../coderules/patterns.md), rule 7) — never string concatenation, which is also an XSS boundary |
| `Image` | `alt` is required by the schema. `treatment` selects a token bundle. Lazy-load below the fold |
| `Video` | `autoplay` implies muted and `playsinline`, always. An autoplaying video with sound on someone's launch page is a defect |
| `CTA` | Scheme allowlist on `href` at render time as well as at generation time — `javascript:`, `data:`, `vbscript:`, protocol-relative all rejected. Defence in depth costs four lines |
| `AbstractVisual` | **Ship one generator here** — `gradient-mesh` — to prove the shape. The other four land in [11](11-visuals-and-slot.md). Seed derives the output deterministically; no user string ever reaches it |
| `Slot` | The sandbox, below |

### The Slot iframe — the one field that becomes code

```html
<iframe srcdoc="…" sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe>
```

**`allow-same-origin` must never be added.** With `allow-scripts` alone the frame has an opaque origin: `localStorage` throws, `document.cookie` is unavailable, `parent.document` throws, no credentialed request is possible. Adding `allow-same-origin` alongside `allow-scripts` lets the frame remove its own sandbox attribute and defeats the whole control.

Also never granted: `allow-top-navigation`, `allow-popups`, `allow-modals`, `allow-forms`, `allow-downloads`.

Second layer, inside the srcdoc:

```
default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:;
```

Tokens are injected into the srcdoc as CSS variables **through `to-css-vars`**, not by string interpolation of raw values. srcdoc content is assembled by concatenation and is the one place a bad token value lands directly in markup.

### The review page

`app/dev/primitives/page.tsx` — every one of the 11 primitives, every one of the 6 layouts, under `cinematic-dark`, driven by the fixtures from phase 01 including `hostile.ts`.

**This page is the standing judgment surface for the rest of v1.** It is how you notice that a change to `--measure` broke the split layout, and it is what phase 11 and every later art direction get compared against. Build it early in the phase, not at the end.

---

## Verify

**The gate** — green, and the renderer-specific rules actually firing:

- [ ] Add a `mode` prop to a block, confirm lint fails, remove it
- [ ] Add `typeof window` inside `renderer/`, confirm lint fails, remove it
- [ ] Add a Tailwind class to a block, confirm lint fails, remove it

**Renderer** ([../spec.md](../spec.md) → Verification, row 3)

- [ ] All 11 primitives render under all 6 layouts where the combination is legal
- [ ] `hostile.ts` — maximum-length copy in every field — does not break a single layout. This is the fixture that predicts real briefs
- [ ] **No snapshot tests.** A snapshot on a design surface fails on every intentional improvement and trains you to update it without looking ([../../techstack/frontend.md](../../techstack/frontend.md))

**Logical properties** ([../spec.md](../spec.md) → Verification, row 7)

- [ ] `dir="rtl"` on the root mirrors the entire review page with **no stylesheet change**. This is the only cheap moment to find out the renderer was authored physically

**Accessibility and motion**

- [ ] `prefers-reduced-motion: reduce` collapses every intent to opacity-only, via the wrapper passing `REDUCED_MOTION` — not via a branch inside a block
- [ ] The in-page motion toggle works, and lives in the runtime rather than in the art direction
- [ ] Every `Image` in every fixture has non-empty `alt`
- [ ] JS disabled: the review page is complete and readable. Nothing is `opacity: 0`

**Security — the rows that go live in this phase** ([../../security/testing.md](../../security/testing.md))

- [ ] **Sandbox escape, executed inside a real `srcdoc` iframe, not jsdom.** `localStorage` throws · `document.cookie` unavailable · `parent.document` throws · `fetch` to any origin fails · top navigation does not occur. Playwright, five assertions
- [ ] XSS payloads in every text prop render as visible characters, asserted headlessly
- [ ] `CTA.href` with `javascript:`, `data:`, `vbscript:`, and `//evil.example` are all refused at render
- [ ] `dangerouslySetInnerHTML` appears nowhere outside the Slot path — the lint rule proves it, and the manual checklist re-reads it

**Judgment — the hard gate**

- [ ] The rendered hero matches or beats the phase 02 comp. If the comp is better, the tokens or the primitives are lying about what the comp contained
- [ ] Scenes read as *paced*, not as a list. Scene padding is generous; a cinematic experience earns its pace by giving each beat room
- [ ] 900ms feels correct rather than slow. It will feel wrong next to typical web UI motion, and that is the point — resist speeding it up to match app conventions
- [ ] You would show this to someone

---

## Skipped

| Not built | Trigger |
|---|---|
| Four of the five `AbstractVisual` generators | [Phase 11](11-visuals-and-slot.md). One proves the shape; five is tuning work best done when there is generated content to tune against |
| `slides` mode | v1 renders `scroll` only |
| The visual verification loop | v2, and it cannot be built before the thing it inspects ([../../techstack/pipeline-tools.md](../../techstack/pipeline-tools.md)) |
| CSS scroll-driven animation | Firefox stable still flags it. Adopt as progressive enhancement when it Baselines; JS-driven reveals stay the floor |
| Hand-written `useMemo` / `useCallback` | The React Compiler handles it. Only if a profiler shows the compiler skipped a component that matters ([../../coderules/performance.md](../../coderules/performance.md)) |

---

## Exit gate

- [ ] `SceneRenderer` is pure: no `mode`, no env read, no window check — enforced, not intended
- [ ] All 11 primitives, all 6 layouts, rendering the three fixtures
- [ ] RTL mirrors with no stylesheet change
- [ ] Reduced motion collapses everything, both ways
- [ ] Sandbox suite passes in a real browser
- [ ] Review page exists and is the thing you look at
- [ ] **It looks genuinely good.** Phase 06 does not start until this line is true
