# Content & Web

Defending the viewer. Everything here protects someone who opens a deck — your customer's prospect, on your customer's pitch, from a downloaded file.

**Rewritten 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)). The change that matters to this document: **the model now writes each slide's HTML and CSS.** Until v3 the model filled a JSON form and React escaped it, so there was no markup to defend against. That control is gone, and what replaced it is below.

## The artefact is a file

One self-contained `.html` file that runs offline: `connect-src 'none'`, fonts and images embedded as data URIs, one script (our player). It talks to *nothing*. There is no CDN to poison, no origin to route around, no beacon to misdirect.

There is no hosted URL in v4. If one is ever built it serves the same bytes, and the S3, CDN and custom-domain controls at the end of this document return with it.

## AI-written HTML and CSS

**Assume the model is compromised.** A slide's markup is attacker-influenced text: pasted material and web search results reach the prompt. The design goal is unchanged from v1 — a fully attacker-controlled model produces an ugly deck, not a dangerous one — and it is now held by three independent layers. **Any one of them alone stops script execution and data exfiltration.** The specification is [../v4/engine.md](../v4/engine.md) → "Security of AI-written HTML".

### Layer 1 — the sanitizer (`nh3`, an allowlist)

| Allowed | Removed |
|---|---|
| A short list of text and structure tags, plus our empty components `dd-image`, `dd-chart`, `dd-texture` | `script`, `svg`, `a`, `img`, `form`, `input`, `iframe`, `object`, `embed`, and everything unlisted |
| `class` (a strict pattern), `data-field` (must name one of this slide's fields), a few `data-*` flags, enum attributes on `dd-*` | `style`, `id`, every `on*` handler, `href`, `src` |
| ≤150 elements, depth ≤12, ≤16 KB of HTML and of CSS per slide | Over-limit slides fail and go to repair |

Three decisions in that table do more than the rest:

- **Slides contain no `<a>`.** A URL is plain text. v3 rendered an unvalidated CTA `href` while inline script was allowed, which was a `javascript:` XSS. v4 does not filter link schemes; it has no link element, so the class is gone.
- **Slides contain no `<img>` and no `<svg>`.** Images and charts are empty `dd-*` elements that *our* code fills after sanitising, from assets and `Fact`s it holds. The model never supplies a `src` or a path.
- **No `style` attribute.** All CSS is in the slide's one stylesheet, where it can be linted.

### Layer 2 — the CSS lint (`tinycss2`)

The lint **rejects**; it never rewrites.

- **No `url()`**, anywhere. This is the exfiltration channel CSS has, and textures reach a slide only through `dd-texture`.
- **No at-rules of any kind**: no `@import`, `@font-face`, `@keyframes`, `@media`.
- **No `animation` or `transition`.** The player owns motion.
- **No `position: fixed`**, no `:host`, `:root`, `html` or `body` selectors, no backslash escapes.
- **The token rule**: colour, font family, size and weight only through the theme's custom properties.
- **The design bans**: no gradients, no blur, no glow ([../design/principles.md](../design/principles.md) §5).

**Scoping is the browser's job.** Each slide lives in its own Declarative Shadow DOM root (`<template shadowrootmode>`, Baseline 2024), so its CSS cannot reach the player or another slide. Selector rewriting was considered and rejected: a rewriting bug is a leak, and the browser already does this correctly.

### Layer 3 — the browser

| Where | Control |
|---|---|
| **QA render** (the worker's Chromium) | Every request is aborted except `data:`. The page's CSP is `script-src 'none'`, and our measure script is injected from outside |
| **Editor** | A `srcdoc` iframe with `sandbox="allow-same-origin"` and **no `allow-scripts`**. The parent drives `contenteditable="plaintext-only"` on `data-field` nodes, so a paste cannot add markup |
| **Export** | The CSP below. The only script is our player, allowed by hash |

**Never combine `allow-scripts` with `allow-same-origin`** on a frame showing slide markup: together they let the framed document remove its own sandbox. Present mode shows the export, which runs our player, so that frame has `allow-scripts` and **not** `allow-same-origin`.

### Why layers, and not the sanitizer alone

DOMPurify, the best sanitizer in its class, had four XSS bypasses disclosed in eighteen months ([platform-and-packages.md](platform-and-packages.md)). `nh3` will have its own. A design that trusted sanitisation alone would be exploitable each time. Here a sanitizer bypass lands in a document that cannot run script and cannot make a request, which is the actual control.

## CSP

**The exported deck**, as a `<meta>` in the file:

```
default-src 'none';
script-src  'sha256-<player>';
style-src   'unsafe-inline';
img-src     data:;
font-src    data:;
connect-src 'none';
base-uri    'none';
form-action 'none';
```

`connect-src 'none'` is the whole point. `img-src data:` and `font-src data:` are what make embedded fonts and images legal under it. `script-src` names one hash: the player. Model-written markup cannot add a script the policy would run.

`style-src 'unsafe-inline'` is required because the theme and each slide's stylesheet are inline. It is why layer 2 exists.

`frame-ancestors` cannot be set from a `<meta>`, so a deck file can be framed by anyone. That is accepted: the deck has no session and no privileges, and it contains no links, so there is nothing to hijack a click *into*. If a deck ever carries anything interactive and consequential, revisit.

**The editor's slide document:** `default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:`.

**App routes:** `frame-ancestors 'none'`, no `unsafe-inline` script.

## Speaker notes do not leave with the deck

Notes are written for the presenter and can be candid. One export that carried them would hand them to every recipient.

| Flavour | Notes |
|---|---|
| **present** | Included, as an inert `<script type="application/json">` block the presenter popup reads |
| **send** — and the PDF | **Not in the file.** Not hidden: absent |

A test asserts on the bytes of the send flavour ([testing.md](testing.md)).

## AI disclosure

EU AI Act Article 50 has been in force since 2026-08-02.

- Every export carries machine-readable markers, and a visible disclosure line in the player chrome (not on the slides).
- Every generated image carries the IPTC XMP tag `digitalSourceType=trainedAlgorithmicMedia`, because the image is what gets copied out of a deck.
- Check the Code of Practice's required mechanism, C2PA or otherwise, at phase 26.

## Theme tokens

The theme is computed by **our code** from a seeded sampler ([../v4/design-engine.md](../v4/design-engine.md) → "Sampler and theme"). No model writes it.

The user-influenced input is the brand kit: typed colours. **Every token value is validated by type before it becomes CSS.**

| Token kind | Validation |
|---|---|
| Colours | Parsed into a colour object, contrast-corrected, re-serialised. Never passed through as a string |
| Numbers | Numeric, range-checked |
| Font families | Selected from the vendored registry by id. **Never a user-supplied string** |

Rejected outright: `url(`, `expression(`, `@import`, `</style`, `javascript:`, backslash escapes. A user-supplied font-family string is the most natural-looking free-text token in the system and the one that most easily carries a payload, which is why it does not exist.

## Text and data

- **Field text** reaches a slide as text nodes. In the editor, `plaintext-only` editing and a server-side re-sanitise on every save keep it that way.
- **Chart data** is drawn by our code as SVG paths and text nodes, never interpolated into markup. A label containing `<script>` renders as visible characters.
- **Generated images** are re-encoded to webp by Pillow and embedded as data URIs. An image cannot execute.
- **Source lines** show a citation's title and host as text. The URL is never a link.

## Uploads

**Logo upload returns in phase 38** (`api/engine/components/logo.py`). The controls below are built: the size cap before reading, magic bytes, dimensions before decode with Pillow's pixel cap set, a fresh PNG re-encode (no metadata, no trailing bytes), and SVG drawn to pixels inside an `<img>` on a Chromium page with every request aborted — so no user SVG reaches a slide and no SVG sanitizer is needed. Still open: running ingest in the isolated upload worker (phase 29), and server-made storage keys once kits are saved.

When logo or file upload returns, every uploaded file is hostile until proven otherwise, and these come back with it:

| Control | Why |
|---|---|
| Magic-byte verification | Extension and `Content-Type` are attacker-supplied |
| Server-side re-encode for raster images | Strips EXIF, kills polyglots, normalises format |
| Dimension and size caps before decode | A 200 KB PNG can decode to gigabytes |
| Server-generated storage keys | User filenames mean path traversal |
| SVG sanitised **and** used only via `<img>` | The layering is the control, not the sanitizer |
| Parsing in an isolated process with nothing to steal | [infrastructure.md](infrastructure.md) |

## If a hosted URL is ever built

Not in v4; the trigger is in [../v4/spec.md](../v4/spec.md). These controls were specified for v3 and return unchanged: a private bucket behind the CDN's origin access control, separate buckets per origin, server-set `Content-Type` with `nosniff`, `Referrer-Policy: no-referrer`, and for custom domains a TXT ownership challenge with periodic re-verification, where an unbound hostname stops being *servable* and not merely owned. Dangling DNS runs both ways: inventory your own records and remove them when a service is retired.
