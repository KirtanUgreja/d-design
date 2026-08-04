# Frontend

Two very different frontends share one component tree: an editor that must feel instant, and a published artifact that must weigh almost nothing. The rule that keeps them from becoming two codebases is [../coderules/patterns.md](../coderules/patterns.md)'s pure renderer — **the same React components produce both**, and neither knows which one it is.

## The published artifact

Publishing runs `renderToString` on the scene tree and writes HTML to S3. The page then **hydrates**, and Motion drives every reveal exactly as it does in the editor.

The alternative — render to HTML and ship a small hand-written IntersectionObserver runtime instead of React — would produce a lighter page and was rejected for one reason: **it implements motion twice.** Motion's vocabulary in the editor, vanilla in the published page, and the two drift. The whole product rests on what you edit being what you ship, and a second motion implementation is that guarantee quietly leaking away. A page that is 60KB heavier is a worse page; a page that animates differently from the editor is a broken product.

**What that costs, and how it is paid:**

| | |
|---|---|
| **Weight** | React + Motion is real JS on a marketing page. It is also the *only* JS — no analytics SDK, no tag manager, no framework chrome. The budget in [../coderules/performance.md](../coderules/performance.md) is spent here deliberately |
| **The real weight is elsewhere** | Images, video, and fonts dominate a page like this by an order of magnitude. Optimizing them matters more than the runtime, and that is where the caps live |
| **Nothing is server-rendered at request time** | The HTML is already on a CDN. Hydration is the only cost, and it happens after first paint |

**Progressive enhancement is the floor.** The page must be readable and complete before hydration — text, images, and layout are in the HTML. If JS never arrives, a viewer sees a finished page without motion, not an empty one. Reveals animate *in* from a visible resting state, never *out* of `opacity: 0`, because an unhydrated `opacity: 0` is a blank page.

CSS scroll-driven animations (~84% support, not yet Baseline) are the progressive-enhancement path already noted in [../v1/art-direction.md](../v1/art-direction.md) — worth adopting for the simple reveals once Firefox ships, because it moves work off the main thread. Not a reason to change the architecture now.

### What talks to the network

The published page was originally specified with `connect-src 'none'` — literally zero outbound requests. Two features broke that, and it is worth being precise about what remains rather than pretending the guarantee is intact.

| Request | Why |
|---|---|
| Five personalization fields, on `/r/<token>` pages only | The artifact is one static shell; the recipient's fields are fetched and slotted in |
| The analytics beacon | Scroll depth, CTA reach, duration — the metrics the product sells |

```
connect-src https://api.<domain>/r/fields https://api.<domain>/v/beacon;
```

**Exact paths, nothing else, not even `'self'`.** The guarantee degrades from *"this page cannot talk to anything"* to *"this page can talk to two endpoints you own, and a browser test proves it talks to nothing else."* That is weaker and still strong. The test in [../security/testing.md](../security/testing.md) changes from *zero requests* to *these two requests and no others*, asserted in a real browser.

The personalization fetch is the one to watch. It puts a recipient token in a client-side request, which is why `Referrer-Policy: no-referrer` and `Cache-Control: private, no-store` matter more now, not less.

## The editor

### State: Zustand

The editor holds one mutable document — the scene tree — plus selection, undo/redo, and in-flight patches. That is a single store, not a graph of independent atoms, and Zustand fits it without a provider tree or a reducer ceremony.

```
useEditor: { tree, selection, patch(blockId, props), undo(), redo(), status }
```

**Undo/redo is the reason a real store earns its place.** It is a stack of past trees with structural sharing, and it is the feature that makes AI-assisted editing safe to try — a user who can undo instantly will experiment, and experimentation is where this product is fun. Build it with the editor, not after.

Patching **one block** and re-rendering the minimum is the performance rule from [../coderules/performance.md](../coderules/performance.md). The React Compiler ([../coderules/tooling.md](../coderules/tooling.md)) handles the memoization automatically, so the store's job is only to make the patch surgical — not to hand-tune renders.

### UI: shadcn/ui

Copy-in components on Radix primitives and Tailwind. Radix gives the accessibility behavior — focus traps, dismissible layers, keyboard navigation — that is genuinely easy to get subtly wrong and that [../coderules/README.md](../coderules/README.md) says never to simplify away. Nothing ships as a runtime dependency.

**Tailwind stays on app chrome only.** The published output is CSS custom properties from the art direction, never utility classes. This is the no-styling invariant seen from the other side: if a Tailwind class ever reaches a rendered block, the art direction has stopped being the single source of visual truth. A lint rule scoped to `renderer/` enforces it.

The property panel, outline editor, brand kit, and settings are the cold 90% of the app ([../coderules/performance.md](../coderules/performance.md)) — assemble them, do not craft them. The craft budget belongs to the renderer.

### Streaming: SSE over a Route Handler

Generation streams scene by scene, so the user watches the experience assemble and can abort a bad direction early — a perceived-performance decision from [../v1/ai-pipeline.md](../v1/ai-pipeline.md).

A `ReadableStream` from an App Router route, `EventSource` in the client. No dependency.

The reason this does not need a streaming library: **the unit is a whole validated scene, not a token.** Partial-object streaming, JSON repair mid-stream, and chat-shaped hooks solve problems this pipeline does not have. A scene is generated, Zod-parsed, and then emitted as one event — anything that failed validation never reaches the client at all.

```
event: scene   data: { "index": 2, "scene": { … } }
event: repair  data: { "index": 3 }
event: done    data: { "count": 8 }
```

You write the reconnect logic. That is a few lines, and it is the only thing the platform does not give you.

**Serialize the good streams to a file.** Because the events are whole validated scenes rather than tokens, an event log replayed client-side drives the same renderer and is indistinguishable from a live run. That makes it three things at once for the price of writing a file: the marketing site's demo ([../design/website.md](../design/website.md)), a way to develop the generation-watch UI without spending a model call per reload, and a regression fixture for the renderer. Keep them versioned alongside the golden briefs ([../v1/plan/06-model-seam-and-build.md](../v1/plan/06-model-seam-and-build.md)).

## Fonts

Fontsource, open-license families, self-hosted on `assets.<domain>` — which the CSP already required (`font-src https://assets.<domain>`).

**Licensing is the reason, not cost.** These fonts are served to your customers' audiences, not to you. That is redistribution, and it makes the licence terms a product constraint rather than a developer detail. Open licences are unambiguous about it; a webfont licence bought per-domain is not, and a product whose whole feature is *publishing to arbitrary domains* would be in permanent violation.

Noto covers all four scripts v3 needs — Latin, CJK, Arabic, Cyrillic — which matters because [../v3/localization.md](../v3/localization.md) requires each art direction to declare a face per script that preserves its *character*. A missing CJK face flattens three distinct art directions into one generic one.

Subset per script, `font-display: swap`, preload the display face.

**Buying type is the highest-leverage money in the product**, and it is deferred rather than refused. Type is most of why `cinematic-dark` will or will not look expensive. Revisit when the three-AD system in v2 makes the difference visible; open faces are good enough to prove the runtime first.

**None of the above binds our own chrome, and that distinction is worth not losing.** The redistribution argument applies to fonts served to *customers' audiences* through published artifacts. Our marketing site and app chrome serve fonts to visitors of our own site, which is what an ordinary webfont licence is for — so the identity face can be a commercially licensed editorial one for the price of a licence rather than waiting on the output's constraint ([../design/brand.md](../design/brand.md)). It **must not** be shared with any art direction's stack: if the chrome and an art direction wear the same face, the chrome starts reading as an art direction and the two design systems have quietly merged.

## Testing

Vitest for units and component behavior. **Playwright for anything that needs a real browser** — and in this product that is most of what matters:

- Sandbox escape assertions, executed inside a real `srcdoc` iframe
- The `connect-src` assertion — that a published page makes exactly two requests and no others
- Cache-deception probes against the real CDN
- Cross-origin behavior, which is the whole architecture and cannot be tested in jsdom

Playwright is already in the fetch worker for screenshots ([backend.md](backend.md)), so it is not a new dependency.

**Renderer quality gets a visual check, not a snapshot test.** A snapshot on a design surface fails on every intentional improvement and trains you to update it without looking. One page rendering all primitives under each art direction, reviewed by eye — that judgment is the product.
