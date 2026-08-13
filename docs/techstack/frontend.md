# Frontend

Two very different frontends share one component tree: an editor (v2) that must feel instant, and an exported deck that must be a single offline file weighing almost nothing. The rule that keeps them from becoming two codebases is [../coderules/patterns.md](../coderules/patterns.md)'s pure renderer — **the same React components produce both**, and neither knows which one it is.

## The exported deck

Publishing renders the deck tree to the single-file HTML — fonts, images, and motion inlined — and writes it to disk (v1) or S3 (v3). The file then needs no hydration: it is self-contained and progressive by design.

The alternative — render to HTML and ship a small hand-written IntersectionObserver runtime instead of React — would produce a lighter page and was rejected for one reason: **it implements motion twice.** Motion's vocabulary in the editor, vanilla in the published page, and the two drift. The whole product rests on what you edit being what you ship, and a second motion implementation is that guarantee quietly leaking away. A page that is 60KB heavier is a worse page; a page that animates differently from the editor is a broken product.

**What that costs, and how it is paid:**

| | |
|---|---|
| **Weight** | The motion and present runtime is tiny and inlined in the single file. It is the *only* JS — no analytics SDK, no tag manager, no framework chrome. The budget in [../coderules/performance.md](../coderules/performance.md) is spent here deliberately |
| **The real weight is elsewhere** | Generated images and embedded fonts dominate a deck by an order of magnitude. Optimizing them matters more than the runtime, and that is where the caps live |
| **Nothing is server-rendered at request time** | The exported file is already complete. Opening it costs nothing; a hosted URL (v3) serves the same static bytes from a CDN |

**Progressive enhancement is the floor.** The deck must be readable and complete without JS — text, images, and layout are in the HTML. If JS never arrives, a viewer sees a finished deck without motion, not an empty one. Reveals animate *in* from a visible resting state, never *out* of `opacity: 0`, because a JS-less `opacity: 0` is a blank slide.

CSS scroll-driven animations (~84% support, not yet Baseline) are the progressive-enhancement path already noted in `v1/plan/06-renderer.md` — worth adopting for the simple reveals once Firefox ships, because it moves work off the main thread. Not a reason to change the architecture now.

### What talks to the network

The **v1 artefact is a single self-contained `.html` file that runs offline** — it talks to *nothing*. `connect-src 'none'` is not a weakening to manage; it is the product. The file is complete without JS (progressive enhancement is the floor), and a browser test asserts it makes zero network requests. The hosted URL (v3) serves the same bytes, so the same assertion holds there.

This reverses the old framing: the previous product weakened `connect-src 'none'` to two endpoints for personalization and analytics. The offline single-file deck has neither.

## The editor (v2)

The editor arrives in v2 (`docs/v2/plan/12-editor.md`) — v1 is the lean flow (interview → mapping → build → review → export) with no editor. The design below is what v2 builds, and the decisions that are expensive to retrofit are made now.

### State: Zustand

The editor holds one mutable document — the deck tree — plus selection, undo/redo, and in-flight patches. That is a single store, not a graph of independent atoms, and Zustand fits it without a provider tree or a reducer ceremony.

```
useEditor: { tree, selection, patch(blockId, props), undo(), redo(), status }
```

**Undo/redo is the reason a real store earns its place.** It is a stack of past trees with structural sharing, and it is the feature that makes AI-assisted editing safe to try — a user who can undo instantly will experiment, and experimentation is where this product is fun. Build it with the editor, not after.

Patching **one block** and re-rendering the minimum is the performance rule from [../coderules/performance.md](../coderules/performance.md). The React Compiler ([../coderules/tooling.md](../coderules/tooling.md)) handles the memoization automatically, so the store's job is only to make the patch surgical — not to hand-tune renders.

### UI: shadcn/ui

Copy-in components on Radix primitives and Tailwind. Radix gives the accessibility behavior — focus traps, dismissible layers, keyboard navigation — that is genuinely easy to get subtly wrong and that [../coderules/README.md](../coderules/README.md) says never to simplify away. Nothing ships as a runtime dependency.

**Tailwind stays on app chrome only.** The rendered slides are CSS custom properties from the design family, never utility classes. This is the no-styling invariant seen from the other side: if a Tailwind class ever reaches a rendered slide, the design family has stopped being the single source of visual truth. A lint rule scoped to `renderer/` enforces it.

The property panel, outline editor, brand kit, and settings are the cold 90% of the app ([../coderules/performance.md](../coderules/performance.md)) — assemble them, do not craft them. The craft budget belongs to the renderer.

### Streaming: SSE over a Route Handler

Generation streams **slide by slide**, so the user watches the deck assemble and can abort a bad direction early — a perceived-performance decision that beats any raw-speed optimization.

A `ReadableStream` from an App Router route, `EventSource` in the client. No dependency.

The reason this does not need a streaming library: **the unit is a whole validated slide, not a token.** Partial-object streaming, JSON repair mid-stream, and chat-shaped hooks solve problems this pipeline does not have. A slide is generated, Zod-parsed, and then emitted as one event — anything that failed validation never reaches the client at all.

```
event: slide   data: { "index": 2, "slide": { … } }
event: repair  data: { "index": 3 }
event: done    data: { "count": 8 }
```

You write the reconnect logic. That is a few lines, and it is the only thing the platform does not give you.

**Serialize the good streams to a file.** Because the events are whole validated slides rather than tokens, an event log replayed client-side drives the same renderer and is indistinguishable from a live run. That makes it three things at once for the price of writing a file: the marketing site's demo ([../design/website.md](../design/website.md)), a way to develop the generation-watch UI without spending a model call per reload, and a regression fixture for the renderer. Keep them versioned alongside the golden briefs (`docs/v1/plan/08-acceptance.md`).

## Fonts

Fontsource, open-license families — **embedded as data URIs in the single-file deck**, not served. The offline file must work from `file://` with zero network, and embedding is what makes that true (`docs/v1/plan/05-export.md`).

**Licensing is the reason, not cost.** These fonts end up inside a deck the customer redistributes. That is redistribution, and it makes the licence terms a product constraint rather than a developer detail. Open licences (OFL-1.1) are unambiguous about bundling in a downloadable file; a webfont licence bought per-domain is not.

Subset per script, embed the faces the deck actually uses, keep the file lean.

**Buying type is the highest-leverage money in the product**, and it is deferred rather than refused. Type is most of why a design family will or will not look expensive. Revisit when the registry makes the difference visible; open faces are good enough to prove the runtime first.

**None of the above binds our own chrome, and that distinction is worth not losing.** The redistribution argument applies to fonts embedded in *customers'* decks. Our marketing site and app chrome serve fonts to visitors of our own site, which is what an ordinary webfont licence is for — so the identity face can be a commercially licensed editorial one for the price of a licence rather than waiting on the output's constraint ([../design/brand.md](../design/brand.md)). It **must not** be shared with any family's stack: if the chrome and a family wear the same face, the chrome starts reading as a family and the two design systems have quietly merged.

## Testing

Vitest for units and component behaviour in the TypeScript repos (`api` uses pytest — [../coderules/python.md](../coderules/python.md)). **Playwright for anything that needs a real browser** — and in this product that is most of what matters:

- The `connect-src 'none'` assertion — that an exported deck makes **zero** requests, from `file://`
- The data-URI assertion — fonts and images are embedded, no external fetch
- The navigation assertion — arrows, Space, buttons, counter, swipe all work
- Cross-origin behavior of a hosted deck (v3), which cannot be tested in jsdom

Playwright is already in the stack for the vision critic and the print path ([backend.md](backend.md)), so it is not a new dependency.

**Renderer quality gets a visual check, not a snapshot test.** A snapshot on a design surface fails on every intentional improvement and trains you to update it without looking. One page rendering all block types under each design family, reviewed by eye — that judgment is the product.
