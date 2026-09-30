# Frontend

Two things a user sees, built in two different places. **The app** is a Next.js UI that renders no slide. **The exported deck** is one offline file the backend assembles. **Rewritten 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)).

v3 shared one React component tree between an editor and an exporter, on the rule that the same renderer must produce both. v4 keeps the guarantee and drops the mechanism: there is one source of slide HTML, the backend, and both the editor and the export show those bytes.

## The app: UI only

Next.js 16 App Router, React 19, TypeScript strict. It arrives in phase 27.

**`web` has no database, no model key and no renderer.** It calls the API and draws chrome.

| What the user sees | Where it comes from |
|---|---|
| A slide on the canvas | The slide's HTML document from the backend, placed in a `srcdoc` iframe |
| A thumbnail | The QA screenshot the worker already took |
| Present mode | **The export file itself**, in an iframe. What you present is byte-for-byte what you send |
| The three looks | Backend-rendered cover and second slide per look |

### The slide iframe

```html
<iframe sandbox="allow-same-origin" srcdoc="…the slide document from the API…">
```

**`allow-same-origin` without `allow-scripts`.** The slide's document cannot run any script. Because it is same-origin, the parent *can* reach its DOM, which is how inline editing works: our code sets `contenteditable="plaintext-only"` on the slide's `data-field` nodes and listens from outside. `plaintext-only` means a paste cannot introduce markup.

Two rules keep that safe:

- **Never add `allow-scripts`.** Together with `allow-same-origin` it lets the framed document remove its own sandbox.
- The document carries its own CSP meta, `default-src 'none'` plus inline styles and data images and fonts ([../security/content-and-web.md](../security/content-and-web.md)).

Per-slide CSS is scoped by **Declarative Shadow DOM**, so the parent reaches fields through the slide's shadow root. That is one line of code to get wrong in every edit path; keep it in one helper.

**Present mode is a different frame.** The export runs our player script, so that iframe needs `allow-scripts` and therefore must **not** have `allow-same-origin`. Phase 27 verifies fullscreen and the presenter popup work from inside it.

### API types

`openapi-typescript` generates `web/lib/api/schema.d.ts` from FastAPI's OpenAPI ([backend.md](backend.md) → "The API contract"). Never hand-edited; the gate fails on a diff. One typed client module wraps `fetch`, and components never call `fetch` directly.

### Streaming

A build streams from `GET /decks/{id}/events`.

**Web reads it with a fetch-stream reader, not `EventSource`.** `EventSource` cannot send an `Authorization` header, and phase 29 needs a Bearer token. Building on `fetch` from phase 27 means auth does not force a rewrite of the generation watch.

- On reconnect the client sends `Last-Event-ID` and the API replays what was missed.
- The unit is a whole checked slide. Ghost slots fill in place as `slide_ready` arrives.
- **Dev proxy:** Next rewrites `/api/*` to FastAPI so everything is same-origin. **Verify the rewrite does not buffer the stream** at phase 27; if it does, the events route is fetched from the API origin directly with CORS for that one route.

### UI: shadcn/ui and Tailwind 4

Copy-in components on Radix primitives, styled with our brand tokens ([../design/brand.md](../design/brand.md)): light warm-neutral, hairlines instead of shadows, one quiet accent. Radix supplies focus traps, dismissible layers and keyboard navigation, which [../coderules/README.md](../coderules/README.md) says never to simplify away.

**Tailwind is for our chrome only and cannot reach a slide**: slides live in an iframe, in a shadow root, with their own stylesheet. v3 imported Tailwind, used none of it, and hand-wrote 578 lines of CSS.

The shadcn defaults are a starting point, not an identity ([../design/principles.md](../design/principles.md) §5).

### State

The server holds the deck and its versions, so undo and redo are server operations. Client state is what is on screen: the selected slide, an in-flight edit, the stream. Whether that needs Zustand is decided in phase 28.

Edits can be refused with **409 while a build runs** ([backend.md](backend.md) → "Data"). The editor shows that as "still generating", not as an error.

## The exported deck

One `.html` file, assembled by the backend (`api/engine/export/`). It is the product.

| Part | What it is |
|---|---|
| **Slides** | Each slide's sanitized HTML inside a `<template shadowrootmode="open">`, with its linted CSS. Declarative Shadow DOM is Baseline since 2024, so no script is needed to scope styles |
| **Theme** | One `:root` block of custom properties. Custom properties and fonts inherit through the shadow boundary |
| **Player** | Our one script, `player.js`, inlined and allowed by hash. Keys, touch, fullscreen, overview grid, deep links, presenter popup, and **all motion** |
| **Fonts** | Vendored Latin-subset woff2, base64 in `@font-face`. Embedded as-is |
| **Images** | webp data URIs |
| **Components** | `dd-chart`, `dd-image` and `dd-texture`, filled by our code after sanitising. A chart is inline SVG drawn from `Fact`s |

**The slide's own CSS may not animate.** No `animation`, no `transition`, no at-rules. The player applies the theme's motion character to slides, so motion is implemented once and `prefers-reduced-motion` is honoured in one place.

**Without JavaScript the deck is still complete.** Slides and styles are plain HTML. A viewer with scripts blocked sees every slide in order, without navigation or motion. Nothing starts at `opacity: 0`.

**Canvas.** Every slide is 1920×1080, scaled to fit by the player and letterboxed in the slide's own ground colour. Print CSS gives one 16:9 page per slide, which is what the PDF is.

### Two flavours

| Flavour | Speaker notes | Used for |
|---|---|---|
| **present** | Included, as an inert `<script type="application/json">` block the presenter popup reads | Presenting from your own machine |
| **send** | **Absent from the file** | Emailing, attaching, and the PDF |

Notes are written for the presenter. A single file that carried them would leak them to every recipient, so "send" is assembled without them rather than hiding them.

### What talks to the network

**Nothing.** The file carries `default-src 'none'` and `connect-src 'none'` in a CSP meta tag. A browser test opens both flavours from `file://` and fails on any request ([../security/testing.md](../security/testing.md)).

The presenter popup is opened by the deck and driven through the window reference, with an in-window fallback when popups are blocked. It needs no network and no `BroadcastChannel`, which is unreliable from `file://`.

## Fonts

~40 OFL families, vendored in `api/engine/design/fonts/` as **Latin-subset woff2** with a licence file per family.

**Licensing is the reason, not cost.** These fonts end up inside a file the customer redistributes. OFL-1.1 permits bundling and embedding; a per-domain webfont licence does not. "It is on Google Fonts" is not a licence check — verify per family.

**Fonts are embedded as-is. `fontTools` subsetting is deferred.** Subsetting a font is modifying it, and under the OFL a modified version may not use the font's Reserved Font Name. Embedding the unmodified vendored file avoids that question entirely. **Trigger to revisit:** a non-Latin locale, or fonts passing 1 MB of an export. When it fires, the answer is to check each family's Reserved Font Name declaration, not to subset blindly.

**Buying type is still the highest-leverage money in the product**, deferred until the phase-23 wall shows where open faces fall short.

**None of this binds our own chrome.** The app's identity face can be commercially licensed, and it must not be a face from the output registry: if the chrome and a deck wear the same face, the two design systems have merged ([../design/brand.md](../design/brand.md)).

## Testing

pytest owns the artefact; Vitest and Playwright own the app.

- **Zero requests from `file://`**, both flavours, in a real browser
- **The send flavour contains no speaker notes** — assert on the bytes
- Navigation: arrows, Space, Home/End, swipe, fullscreen, overview, deep link, presenter popup
- The deck is complete with scripts blocked
- **The hostile-slide suite** on Chromium, Firefox and WebKit ([../security/testing.md](../security/testing.md))
- App: a Playwright E2E against a stub engine replaying a recorded `events.jsonl`, plus one live run per phase exit

**Design quality gets a human, not a snapshot.** A snapshot on a design surface fails on every intentional improvement and trains you to update it without looking. The bench wall, scored by the owner, is that check ([../v4/bench.md](../v4/bench.md)).
